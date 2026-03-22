"""Brainrot video pipeline - configurable."""
from __future__ import annotations

import json
import subprocess
import zipfile
import urllib.request
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.paths import PROJECT_ROOT

FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

TTS_VOICES = ["alloy", "ash", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"]
TTS_MODELS = ["tts-1", "tts-1-hd"]

GPT_MODELS = [
    "gpt-5.4",
    "gpt-5.4-2026-03-05",
    "gpt-5.3-chat-latest",
    "gpt-5.2",
    "gpt-5.2-2025-12-11",
    "gpt-5.1",
    "gpt-5.1-2025-11-13",
    "gpt-5",
    "gpt-5-2025-08-07",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4o-2024-11-20",
]
ASS_FONTS = ["Arial", "Arial Black", "Impact", "Helvetica", "Verdana", "Comic Sans MS"]


def _overlay_png(root: Path, basename: str) -> Path:
    """Resolve peter.png / stewie.png from project root or assets/."""
    for base in (root, root / "assets"):
        p = base / basename
        if p.is_file():
            return p
    raise FileNotFoundError(f"Missing {basename} — place it in {root} or {root / 'assets'}")


def _rgb_to_ass(color: str) -> str:
    """#RRGGBB -> &H00BBGGRR"""
    c = color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return f"&H00{b:02x}{g:02x}{r:02x}"


@dataclass
class Config:
    topic: str = ""
    dialogue: list[dict[str, str]] = field(default_factory=list)
    dialogue_lines: int = 8
    tts_speed: float = 1.2
    shake_speed: float = 15
    font_name: str = "Arial Black"
    font_size: int = 100
    text_color: str = "#FDE047"
    outline_color: str = "#000000"
    peter_voice: str = "echo"
    stewie_voice: str = "alloy"
    tts_model: str = "tts-1"
    gpt_model: str = "gpt-5.4"
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
    for n, u in [("ffmpeg", "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"),
                 ("ffprobe", "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip")]:
        zp = cache / f"{n}.zip"
        urllib.request.urlretrieve(u, zp)
        with zipfile.ZipFile(zp, "r") as z:
            with z.open(n) as src, open(cache / n, "wb") as dst:
                shutil.copyfileobj(src, dst)
        (cache / n).chmod(0o755)
        zp.unlink()
    FFMPEG_BIN, FFPROBE_BIN = str(fe), str(fp)


def _get_duration(path: Path) -> float:
    r = subprocess.run([FFPROBE_BIN, "-v", "error", "-show_entries", "format=duration",
                       "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                      capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def generate_dialogue(client: Any, topic: str, dialogue_lines: int, gpt_model: str) -> list[dict[str, str]]:
    """LLM-only: return dialogue list for review (Peter/Stewie lines)."""
    prompt = f"""Unhinged brainrot debate between Peter and Stewie about {topic}.
JSON: {{"dialogue":[{{"speaker":"Peter"|"Stewie","text":"..."}}]}}
**{dialogue_lines} lines**, short punchy."""
    r = client.chat.completions.create(
        model=gpt_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(r.choices[0].message.content)["dialogue"]


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


def run_pipeline(cfg: Config, bg_path: Path, output_path: Path, client: Any, temp_dir: Path, project_root: Path | None = None) -> Path:
    _ensure_ffmpeg()
    temp_dir.mkdir(parents=True, exist_ok=True)

    dialogue = list(cfg.dialogue) if cfg.dialogue else []
    if not dialogue:
        if not (cfg.topic or "").strip():
            raise ValueError("Provide dialogue JSON or a topic (CLI auto-writes script).")
        dialogue = generate_dialogue(client, (cfg.topic or "").strip(), cfg.dialogue_lines, cfg.gpt_model)

    voices = {"Peter": cfg.peter_voice, "Stewie": cfg.stewie_voice}
    segments = []
    for i, line in enumerate(dialogue):
        sp, txt = line["speaker"], line["text"]
        fp = temp_dir / f"line_{i}.mp3"
        client.audio.speech.create(model=cfg.tts_model, voice=voices.get(sp, "onyx"), input=txt).write_to_file(fp)
        segments.append({"file": fp, "speaker": sp, "duration": _get_duration(fp), "text": txt})

    list_f = temp_dir / "concat.txt"
    list_f.write_text("\n".join(f"file '{s['file'].name}'" for s in segments))
    combined = temp_dir / "dialogue.mp3"
    subprocess.run([FFMPEG_BIN, "-y", "-f", "concat", "-safe", "0", "-i", str(list_f), "-c", "copy", str(combined)],
                  check=True, capture_output=True)

    if cfg.tts_speed != 1.0:
        sped = temp_dir / "dialogue_sped.mp3"
        subprocess.run([FFMPEG_BIN, "-y", "-i", str(combined), "-filter:a", f"atempo={cfg.tts_speed}", str(sped)],
                      check=True, capture_output=True)
        combined = sped

    timings, total = [], 0.0
    for s in segments:
        d = s["duration"] / cfg.tts_speed if cfg.tts_speed != 1.0 else s["duration"]
        timings.append({"speaker": s["speaker"], "start": total, "end": total + d})
        total += d

    words = client.audio.transcriptions.create(file=open(combined, "rb"), model="whisper-1",
                                               response_format="verbose_json",
                                               timestamp_granularities=["word"]).words

    pc, oc = _rgb_to_ass(cfg.text_color), _rgb_to_ass(cfg.outline_color)
    ass = temp_dir / "subs.ass"
    ass.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Brainrot,{cfg.font_name},{cfg.font_size},{pc},{oc},{oc},&H00000000,-1,0,0,0,100,100,0,0,1,8,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""", encoding="utf-8")
    with ass.open("a", encoding="utf-8") as f:
        for w in words:
            st = w.start if hasattr(w, "start") else w["start"]
            en = w.end if hasattr(w, "end") else w["end"]
            txt = (w.word if hasattr(w, "word") else w["word"]).strip()
            h, m, s = int(st // 3600), int((st % 3600) // 60), st % 60
            eh, em, es = int(en // 3600), int((en % 3600) // 60), en % 60
            f.write(f"Dialogue: 0,{h}:{m:02}:{s:05.2f},{eh}:{em:02}:{es:05.2f},Brainrot,,0,0,0,,{{\\an5}}{txt}\n")

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
    # 9:16 @ 1080×1920 to match ASS PlayRes; center-crop any aspect (e.g. 16:9 → vertical strip).
    # Looped input + -t total ensures background covers full dialogue when clip is shorter than audio.
    fc = f"""[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg];
[1:v]scale=300:-1[p];[2:v]scale=200:-1[s];
[bg][p]overlay=x='{"+".join(px) or "-w"}':y='{"+".join(py) or "-h"}':enable='{"+".join(pe) or "0"}'[v1];
[v1][s]overlay=x='{"+".join(sx) or "-w"}':y='{"+".join(sy) or "-h"}':enable='{"+".join(se) or "0"}'[v2];
[v2]ass='{ass_path}'[v_out];
[0:a]volume=0.1[a_bg];[3:a]volume=1.0[a_dialogue];
[a_bg][a_dialogue]amix=inputs=2:duration=shortest:dropout_transition=2[a_out]"""

    out = Path(output_path)
    if out.suffix.lower() != f".{cfg.output_format}":
        out = out.with_suffix(f".{cfg.output_format}")

    root = project_root or PROJECT_ROOT
    subprocess.run([FFMPEG_BIN, "-y", "-stream_loop", "-1", "-i", str(bg_path), "-i", str(_overlay_png(root, "peter.png")), "-i", str(_overlay_png(root, "stewie.png")), "-i", str(combined),
                    "-filter_complex", fc, "-map", "[v_out]", "-map", "[a_out]",
                    "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-t", str(total), str(out)],
                   check=True, capture_output=True)
    return out
