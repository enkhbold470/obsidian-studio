"""Brainrot pipeline: LLM dialogue → MOSS-TTSD → ASS subtitles → FFmpeg (bg + PNG overlays + audio)."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import requests
from openai import OpenAI

from core.moss_ttsd import (
    dialogue_lines_to_tagged_text,
    segment_durations_proportional,
    synthesize_dialogue_wav,
)
from core.paths import CORE_ROOT, PROJECT_ROOT
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

_log = logging.getLogger("brainrot.pipeline")


def _pipe_print(msg: str) -> None:
    print(f"[brainrot] {msg}", flush=True)
    _log.info(msg)


@contextmanager
def _verbose_section(verbose: bool, label: str) -> Iterator[None]:
    t0 = time.perf_counter()
    if verbose:
        _pipe_print(f"→ {label} …")
    try:
        yield
    except BaseException as e:
        if verbose:
            _pipe_print(f"← {label} FAILED after {time.perf_counter() - t0:.2f}s — {type(e).__name__}: {e}")
        raise
    if verbose:
        _pipe_print(f"← {label} OK in {time.perf_counter() - t0:.2f}s")


def _subprocess_run(cmd: list[str], *, verbose: bool, what: str) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        _pipe_print(f"{what} failed (exit {r.returncode})")
        if verbose:
            if r.stderr:
                _pipe_print(f"stderr:\n{r.stderr[:8000]}")
            if r.stdout:
                _pipe_print(f"stdout:\n{r.stdout[:2000]}")
        r.check_returncode()


FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

DEFAULT_OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.dedaluslabs.ai/v1").rstrip("/")
_DEFAULT_LLM = "google/gemini-2.5-flash"
DEFAULT_GPT_MODEL_ID = os.environ.get("DEFAULT_GPT_MODEL", _DEFAULT_LLM).strip() or _DEFAULT_LLM


def _json_response_format_supported(model: str) -> bool:
    """Gateways like Dedalus reject response_format for non-OpenAI routes (e.g. google/gemini)."""
    if os.environ.get("LLM_FORCE_JSON_RESPONSE_FORMAT", "").strip().lower() in ("1", "true", "yes"):
        return True
    if os.environ.get("LLM_DISABLE_JSON_RESPONSE_FORMAT", "").strip().lower() in ("1", "true", "yes"):
        return False
    m = (model or "").strip().lower()
    return m.startswith("openai/")


def get_llm_client() -> OpenAI:
    base = os.environ.get("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).rstrip("/")
    return OpenAI(base_url=base)


def get_default_gpt_model() -> str:
    return DEFAULT_GPT_MODEL_ID


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
            # Segment durations match final muxed audio (TTSD: proportional after atempo).
            d = float(s["duration"])
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
    voice_id_peter: str = ""
    voice_id_inky: str = ""
    # If set, MOSS TTSD uses this voice for BOTH [S1] and [S2] (optional). Otherwise use VOICE_ID_*.
    single_voice_id: str = ""
    verbose: bool = True
    tts_model: str = "moss-ttsd"
    gpt_model: str = field(default_factory=get_default_gpt_model)
    output_format: str = "mp4"
    # FFmpeg scale=w:-1 on each overlay PNG (1080×1920 frame). Increase if characters look too small.
    overlay_peter_width: int = 420
    overlay_inky_width: int = 420


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
    return f"""Unhinged brainrot debate between Peter and Inky about: {topic}

Return one JSON object only (no markdown fences, no commentary):
{{"dialogue":[{{"speaker":"Peter","text":"..."}},{{"speaker":"Inky","text":"..."}}]}}

Rules:
- Exactly {dialogue_lines} lines, alternating speakers is fine, short punchy lines.
- speaker must be exactly Peter or Inky (string values). Do not use Stewie or any other name for the second speaker.
- Do NOT put [S1], [S2], or speaker tags inside "text" — plain line text only. The app converts Peter→[S1] and Inky→[S2] for MOSS-TTSD (voice_id = Peter, voice_id2 = Inky).
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


def normalize_dialogue_speakers(lines: list[Any]) -> list[dict[str, str]]:
    """Map common LLM slip-ups (e.g. Stewie) to Inky; normalize Peter casing."""
    out: list[dict[str, str]] = []
    for item in lines:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("speaker", "") or "").strip()
        key = raw.casefold()
        if key == "peter":
            sp = "Peter"
        elif key in ("inky", "stewie"):
            sp = "Inky"
        else:
            sp = raw
        text = str(item.get("text", "") or "")
        out.append({"speaker": sp, "text": text})
    return out


def generate_dialogue(
    client: Any, topic: str, dialogue_lines: int, gpt_model: str, *, verbose: bool = True
) -> list[dict[str, str]]:
    prompt = _dialogue_prompt(topic, dialogue_lines)
    kwargs: dict[str, Any] = dict(
        model=gpt_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8192,
    )
    if _json_response_format_supported(gpt_model):
        kwargs["response_format"] = {"type": "json_object"}

    with _verbose_section(verbose, "LLM chat.completions (dialogue JSON)"):
        r = client.chat.completions.create(**kwargs)
    content = (r.choices[0].message.content or "").strip()
    if not content:
        raise ValueError("Empty LLM response for dialogue.")

    try:
        dialogue = normalize_dialogue_speakers(_parse_dialogue_payload(content))
    except ValueError:
        if verbose:
            _pipe_print("dialogue JSON invalid — retrying with repair prompt …")
        repair_kw: dict[str, Any] = dict(
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
            max_tokens=8192,
        )
        if _json_response_format_supported(gpt_model):
            repair_kw["response_format"] = {"type": "json_object"}
        with _verbose_section(verbose, "LLM repair pass (dialogue JSON)"):
            r2 = client.chat.completions.create(**repair_kw)
        content2 = (r2.choices[0].message.content or "").strip()
        dialogue = normalize_dialogue_speakers(_parse_dialogue_payload(content2))

    if not is_valid_dialogue(dialogue):
        raise ValueError("Model dialogue failed validation (need Peter/Inky lines with non-empty text).")
    return dialogue


def is_valid_dialogue(lines: Any) -> bool:
    if not isinstance(lines, list) or len(lines) < 1:
        return False
    for item in lines:
        if not isinstance(item, dict):
            return False
        if item.get("speaker") not in ("Peter", "Inky"):
            return False
        if not str(item.get("text", "")).strip():
            return False
    return True


def run_pipeline(
    cfg: Config,
    bg_path: Path,
    output_path: Path,
    llm_client: Any,
    temp_dir: Path,
    project_root: Path | None = None,
) -> Path:
    t0 = time.perf_counter()
    v = cfg.verbose
    _pipe_print(f"start bg={bg_path} → {output_path}")
    with _verbose_section(v, "ensure ffmpeg + ASS support"):
        _ensure_ffmpeg()
    temp_dir.mkdir(parents=True, exist_ok=True)

    dialogue = normalize_dialogue_speakers(list(cfg.dialogue)) if cfg.dialogue else []
    if not dialogue:
        if not (cfg.topic or "").strip():
            raise ValueError("Provide dialogue or a topic.")
        dialogue = generate_dialogue(
            llm_client,
            (cfg.topic or "").strip(),
            cfg.dialogue_lines,
            cfg.gpt_model,
            verbose=v,
        )
    else:
        if v:
            _pipe_print(f"using provided dialogue ({len(dialogue)} lines)")

    dialogue = [d for d in dialogue if str(d.get("text", "")).strip()]
    if not dialogue:
        raise ValueError("No non-empty dialogue lines.")

    voice_peter = (cfg.voice_id_peter or os.environ.get("VOICE_ID_PETER", "")).strip()
    voice_inky = (cfg.voice_id_inky or os.environ.get("VOICE_ID_INKY", "")).strip()
    single = (cfg.single_voice_id or "").strip()
    use_single_env = os.environ.get("MOSS_USE_SINGLE_VOICE_FOR_ALL", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    single_env_id = os.environ.get("MOSS_SINGLE_VOICE_ID", "").strip()
    if single:
        voice_peter = voice_inky = single
    elif use_single_env and single_env_id:
        voice_peter = voice_inky = single_env_id

    if not voice_peter or not voice_inky:
        raise ValueError(
            "Set VOICE_ID_PETER and VOICE_ID_INKY in .env (or Config). "
            "Optional: MOSS_USE_SINGLE_VOICE_FOR_ALL=1 with MOSS_SINGLE_VOICE_ID to force one voice for both [S1]/[S2]."
        )

    if v:
        _pipe_print(
            f"MOSS TTSD: voice_id (Peter / [S1])={voice_peter!r}  voice_id2 (Inky / [S2])={voice_inky!r}  model={cfg.tts_model!r}"
        )
        tagged_preview = dialogue_lines_to_tagged_text(dialogue)
        prev = tagged_preview if len(tagged_preview) <= 200 else tagged_preview[:200] + "…"
        _pipe_print(f"TTSD tagged text preview ({len(tagged_preview)} chars): {prev!r}")

    with _verbose_section(v, "MOSS TTSD synthesize (one or chunked requests)"):
        wav_bytes = synthesize_dialogue_wav(
            dialogue,
            voice_id=voice_peter,
            voice_id2=voice_inky,
            model=cfg.tts_model,
            ffmpeg_bin=FFMPEG_BIN,
            temp_dir=temp_dir,
        )
    combined = temp_dir / "dialogue.wav"
    combined.write_bytes(wav_bytes)

    if cfg.tts_speed != 1.0:
        sped = temp_dir / "dialogue_sped.wav"
        with _verbose_section(v, f"ffmpeg atempo ({cfg.tts_speed})"):
            _subprocess_run(
                [
                    FFMPEG_BIN,
                    "-y",
                    "-i",
                    str(combined),
                    "-filter:a",
                    f"atempo={cfg.tts_speed}",
                    str(sped),
                ],
                verbose=v,
                what="ffmpeg atempo",
            )
        combined = sped

    with _verbose_section(v, "ffprobe + proportional segment timings"):
        duration_total = _get_duration(combined)
        durations = segment_durations_proportional(dialogue, duration_total)
        segments: list[dict[str, Any]] = [
            {"speaker": line["speaker"], "text": line["text"], "duration": d}
            for line, d in zip(dialogue, durations, strict=True)
        ]
        if v:
            _pipe_print(f"dialogue audio duration {duration_total:.2f}s  lines={len(segments)}")

    timings, total = [], 0.0
    for s in segments:
        d = float(s["duration"])
        timings.append({"speaker": s["speaker"], "start": total, "end": total + d})
        total += d

    ass = temp_dir / "subs.ass"
    with _verbose_section(v, "write ASS subtitles"):
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
    pw, iw = int(cfg.overlay_peter_width), int(cfg.overlay_inky_width)
    fc = f"""[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg];
[1:v]scale={pw}:-1[p];[2:v]scale={iw}:-1[s];
[bg][p]overlay=x='{"+".join(px) or "-w"}':y='{"+".join(py) or "-h"}':enable='{"+".join(pe) or "0"}'[v1];
[v1][s]overlay=x='{"+".join(sx) or "-w"}':y='{"+".join(sy) or "-h"}':enable='{"+".join(se) or "0"}'[v2];
[v2]ass='{ass_path}'[v_out];
[3:a]anull[a_out]"""

    out = Path(output_path)
    if out.suffix.lower() != f".{cfg.output_format}":
        out = out.with_suffix(f".{cfg.output_format}")

    root = project_root or PROJECT_ROOT
    with _verbose_section(v, "ffmpeg encode (bg + overlays + ass + audio → mp4)"):
        _subprocess_run(
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
                str(_overlay_png(root, "inky.png")),
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
            verbose=v,
            what="ffmpeg final encode",
        )
    _pipe_print(f"pipeline SUCCESS total wall {time.perf_counter() - t0:.2f}s → {out}")
    return out
