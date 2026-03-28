"""Brainrot pipeline: LLM dialogue → Kokoro TTS → ASS subtitles → FFmpeg (bg + PNG overlays + audio)."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from openai import OpenAI

from core.paths import CORE_ROOT, PROJECT_ROOT
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")
# print(os.environ.get("OPENAI_BASE_URL"))
# print(os.environ.get("OPENAI_API_KEY"))
# print(os.environ.get("KOKORO_BASE_URL"))
# print(os.environ.get("DEFAULT_GPT_MODEL"))
# print(os.environ.get("KOKORO_API_KEY"))

_log = logging.getLogger("brainrot.pipeline")


def _pipe_print(msg: str) -> None:
    print(f"[brainrot] {msg}", flush=True)
    _log.info(msg)


FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

DEFAULT_OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.dedaluslabs.ai/v1").rstrip("/")
DEFAULT_KOKORO_BASE_URL = os.environ.get("KOKORO_BASE_URL", "https://api.kokoro.dok.inkyg.com/v1").rstrip("/")
DEFAULT_GPT_MODEL_ID = os.environ.get("DEFAULT_GPT_MODEL", "xai/grok-4-fast-reasoning").strip() or "xai/grok-4-fast-reasoning"


def get_llm_client() -> OpenAI:
    base = os.environ.get("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).rstrip("/")
    return OpenAI(base_url=base)


def get_tts_client() -> OpenAI:
    base = os.environ.get("KOKORO_BASE_URL", DEFAULT_KOKORO_BASE_URL).rstrip("/")
    key = os.environ.get("KOKORO_API_KEY", "not-needed")
    return OpenAI(base_url=base, api_key=key)


def get_default_gpt_model() -> str:
    return DEFAULT_GPT_MODEL_ID


def _primary_voice_id(voice: str) -> str:
    first = voice.split("+", 1)[0].strip()
    return first.split("*", 1)[0].strip()


def kokoro_speech_to_file(tts_client: Any, fp: Path, model: str, voice: str, text: str) -> None:
    try:
        tts_client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
        ).write_to_file(fp)
        return
    except Exception as e:
        code = getattr(e, "status_code", None)
        if code not in (400, 422):
            raise
        primary = _primary_voice_id(voice)
        if primary == voice:
            raise
        _pipe_print(f"TTS fallback voice {voice!r} → {primary!r} ({type(e).__name__})")
        tts_client.audio.speech.create(
            model=model,
            voice=primary,
            input=text,
            response_format="mp3",
        ).write_to_file(fp)


def _overlay_png(root: Path, basename: str) -> Path:
    for base in (root, root / "assets", CORE_ROOT / "assets"):
        p = base / basename
        if p.is_file():
            return p
    raise FileNotFoundError(
        f"Missing {basename} — put it in {root}, {root / 'assets'}, or {CORE_ROOT / 'assets'}"
    )


def _rgb_to_ass(color: str) -> str:
    c = color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return f"&H00{b:02x}{g:02x}{r:02x}"


def _write_ass_subtitles_from_segments(ass_path: Path, segments: list[dict[str, Any]], cfg: Config) -> None:
    pc, oc = _rgb_to_ass(cfg.text_color), _rgb_to_ass(cfg.outline_color)
    with ass_path.open("w", encoding="utf-8") as f:
        f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Brainrot,{cfg.font_name},{cfg.font_size},{pc},{oc},{oc},&H00000000,-1,0,0,0,100,100,0,0,1,8,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
        t_run = 0.0
        for s in segments:
            d = s["duration"] / cfg.tts_speed if cfg.tts_speed != 1.0 else s["duration"]
            st_line = t_run
            t_run += d
            text = str(s.get("text", "") or "")
            words = [w for w in text.replace("\n", " ").split() if w.strip()]
            if not words:
                continue
            n = len(words)
            chunk_d = d / n
            for i, w in enumerate(words):
                ws = st_line + i * chunk_d
                we = st_line + (i + 1) * chunk_d
                h, m, sec = int(ws // 3600), int((ws % 3600) // 60), ws % 60
                eh, em, es = int(we // 3600), int((we % 3600) // 60), we % 60
                f.write(
                    f"Dialogue: 0,{h}:{m:02}:{sec:05.2f},{eh}:{em:02}:{es:05.2f},Brainrot,,0,0,0,,{{\\an5}}{w}\n"
                )


@dataclass
class Config:
    topic: str = ""
    dialogue: list[dict[str, str]] = field(default_factory=list)
    dialogue_lines: int = 8
    tts_speed: float = 1.4
    shake_speed: float = 10.0
    font_name: str = "Arial Black"
    font_size: int = 100
    text_color: str = "#FDE047"
    outline_color: str = "#000000"
    peter_voice: str = "am_michael"
    stewie_voice: str = "bm_george"
    tts_model: str = "kokoro"
    gpt_model: str = field(default_factory=get_default_gpt_model)
    output_format: str = "mp4"


def _check_ffmpeg_has_ass(ffmpeg_path: str) -> bool:
    r = subprocess.run([ffmpeg_path, "-h", "filter=ass"], capture_output=True, text=True)
    return "Unknown filter" not in (r.stdout + r.stderr)


def _ensure_ffmpeg() -> None:
    global FFMPEG_BIN, FFPROBE_BIN
    if _check_ffmpeg_has_ass("ffmpeg"):
        return
    cache = PROJECT_ROOT / "temp_build" / "ffmpeg_bin"
    fe, fp = cache / "ffmpeg", cache / "ffprobe"
    if fe.exists() and fp.exists() and _check_ffmpeg_has_ass(str(fe)):
        FFMPEG_BIN, FFPROBE_BIN = str(fe), str(fp)
        return
    cache.mkdir(parents=True, exist_ok=True)
    for n, u in [
        ("ffmpeg", "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"),
        ("ffprobe", "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"),
    ]:
        zp = cache / f"{n}.zip"
        rr = requests.get(u, timeout=120)
        rr.raise_for_status()
        zp.write_bytes(rr.content)
        with zipfile.ZipFile(zp, "r") as z:
            with z.open(n) as src, open(cache / n, "wb") as dst:
                shutil.copyfileobj(src, dst)
        (cache / n).chmod(0o755)
        zp.unlink()
    FFMPEG_BIN, FFPROBE_BIN = str(fe), str(fp)


def _get_duration(path: Path) -> float:
    r = subprocess.run(
        [
            FFPROBE_BIN,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout.strip())


def _strip_code_fence(raw: str) -> str:
    s = (raw or "").strip()
    if not s.startswith("```"):
        return s
    lines = s.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _dialogue_prompt(topic: str, dialogue_lines: int) -> str:
    return f"""Unhinged brainrot debate between Peter and Stewie about: {topic}

Return one JSON object only (no markdown fences, no commentary):
{{"dialogue":[{{"speaker":"Peter","text":"..."}},{{"speaker":"Stewie","text":"..."}}]}}

Rules:
- Exactly {dialogue_lines} lines, alternating speakers is fine, short punchy lines.
- speaker must be exactly Peter or Stewie (string values).
- In each "text" value: do NOT use the double-quote character. Use apostrophes or rephrase (e.g. pizza is good not pizza is "good").
- ASCII only in JSON."""


def _parse_dialogue_payload(content: str) -> list[dict[str, str]]:
    text = _strip_code_fence(content)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        _log.warning("dialogue JSON parse failed: %s (preview %r)", e, text[:400])
        raise ValueError(
            f"Model returned invalid JSON: {e}. "
            "Try again; if it persists, set DEFAULT_GPT_MODEL to a stronger model."
        ) from e
    d = data.get("dialogue")
    if not isinstance(d, list):
        raise ValueError('JSON must contain a "dialogue" array.')
    return d


def generate_dialogue(client: Any, topic: str, dialogue_lines: int, gpt_model: str) -> list[dict[str, str]]:
    prompt = _dialogue_prompt(topic, dialogue_lines)
    kwargs = dict(
        model=gpt_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=8192,
    )

    r = client.chat.completions.create(**kwargs)
    content = (r.choices[0].message.content or "").strip()
    if not content:
        raise ValueError("Empty LLM response for dialogue.")

    try:
        dialogue = _parse_dialogue_payload(content)
    except ValueError:
        _pipe_print("dialogue JSON invalid — retrying with repair prompt …")
        r2 = client.chat.completions.create(
            model=gpt_model,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": content[:12000]},
                {
                    "role": "user",
                    "content": (
                        "That output was not valid JSON (often unescaped \" inside a text field). "
                        "Reply with ONLY one JSON object again. In each text field, never use the "
                        "double-quote character — use apostrophes or rephrase. Same topic and line count."
                    ),
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=8192,
        )
        content2 = (r2.choices[0].message.content or "").strip()
        dialogue = _parse_dialogue_payload(content2)

    if not is_valid_dialogue(dialogue):
        raise ValueError("Model dialogue failed validation (need Peter/Stewie lines with non-empty text).")
    return dialogue


def is_valid_dialogue(lines: Any) -> bool:
    if not isinstance(lines, list) or len(lines) < 1:
        return False
    for item in lines:
        if not isinstance(item, dict):
            return False
        if item.get("speaker") not in ("Peter", "Stewie"):
            return False
        if not str(item.get("text", "")).strip():
            return False
    return True


def run_pipeline(
    cfg: Config,
    bg_path: Path,
    output_path: Path,
    llm_client: Any,
    tts_client: Any,
    temp_dir: Path,
    project_root: Path | None = None,
) -> Path:
    t0 = time.perf_counter()
    _pipe_print(f"start bg={bg_path} → {output_path}")
    _ensure_ffmpeg()
    temp_dir.mkdir(parents=True, exist_ok=True)

    dialogue = list(cfg.dialogue) if cfg.dialogue else []
    if not dialogue:
        if not (cfg.topic or "").strip():
            raise ValueError("Provide dialogue or a topic.")
        _pipe_print("LLM dialogue …")
        dialogue = generate_dialogue(
            llm_client, (cfg.topic or "").strip(), cfg.dialogue_lines, cfg.gpt_model
        )
    else:
        _pipe_print(f"using provided dialogue ({len(dialogue)} lines)")

    voices = {"Peter": cfg.peter_voice, "Stewie": cfg.stewie_voice}
    segments: list[dict[str, Any]] = []
    for i, line in enumerate(dialogue):
        sp, txt = line["speaker"], line["text"]
        fp = temp_dir / f"line_{i}.mp3"
        _pipe_print(f"TTS {i + 1}/{len(dialogue)} {sp} …")
        kokoro_speech_to_file(tts_client, fp, cfg.tts_model, voices.get(sp, "bm_george"), txt)
        segments.append({"file": fp, "speaker": sp, "duration": _get_duration(fp), "text": txt})

    list_f = temp_dir / "concat.txt"
    list_f.write_text("\n".join(f"file '{s['file'].name}'" for s in segments))
    combined = temp_dir / "dialogue.mp3"
    subprocess.run(
        [
            FFMPEG_BIN,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_f),
            "-c",
            "copy",
            str(combined),
        ],
        check=True,
        capture_output=True,
        cwd=str(temp_dir),
    )

    if cfg.tts_speed != 1.0:
        sped = temp_dir / "dialogue_sped.mp3"
        subprocess.run(
            [
                FFMPEG_BIN,
                "-y",
                "-i",
                str(combined),
                "-filter:a",
                f"atempo={cfg.tts_speed}",
                str(sped),
            ],
            check=True,
            capture_output=True,
        )
        combined = sped

    timings, total = [], 0.0
    for s in segments:
        d = s["duration"] / cfg.tts_speed if cfg.tts_speed != 1.0 else s["duration"]
        timings.append({"speaker": s["speaker"], "start": total, "end": total + d})
        total += d

    ass = temp_dir / "subs.ass"
    _write_ass_subtitles_from_segments(ass, segments, cfg)

    shake = cfg.shake_speed
    px, py, pe, sx, sy, se = [], [], [], [], [], []
    for seg in timings:
        s, e = seg["start"], seg["end"]
        if seg["speaker"] == "Peter":
            pe.append(f"between(t,{s},{e})")
            px.append(f"(between(t,{s},{e})*((W-w+50)+max(0,0.2-(t-{s}))*2000))")
            py.append(f"(between(t,{s},{e})*((H/2-h/2)+sin((t-{s})*{shake})*15))")
        else:
            se.append(f"between(t,{s},{e})")
            sx.append(f"(between(t,{s},{e})*(0-max(0,0.2-(t-{s}))*2000))")
            sy.append(f"(between(t,{s},{e})*((H/2-h/2)+sin((t-{s})*{shake})*15))")

    ass_path = str(ass).replace("\\", "/").replace(":", "\\:")
    fc = f"""[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg];
[1:v]scale=300:-1[p];[2:v]scale=200:-1[s];
[bg][p]overlay=x='{"+".join(px) or "-w"}':y='{"+".join(py) or "-h"}':enable='{"+".join(pe) or "0"}'[v1];
[v1][s]overlay=x='{"+".join(sx) or "-w"}':y='{"+".join(sy) or "-h"}':enable='{"+".join(se) or "0"}'[v2];
[v2]ass='{ass_path}'[v_out];
[3:a]anull[a_out]"""

    out = Path(output_path)
    if out.suffix.lower() != f".{cfg.output_format}":
        out = out.with_suffix(f".{cfg.output_format}")

    root = project_root or PROJECT_ROOT
    subprocess.run(
        [
            FFMPEG_BIN,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(bg_path),
            "-i",
            str(_overlay_png(root, "peter.png")),
            "-i",
            str(_overlay_png(root, "stewie.png")),
            "-i",
            str(combined),
            "-filter_complex",
            fc,
            "-map",
            "[v_out]",
            "-map",
            "[a_out]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-c:a",
            "aac",
            "-t",
            str(total),
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    _pipe_print(f"done in {time.perf_counter() - t0:.1f}s → {out}")
    return out
