"""Brainrot video pipeline - configurable."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openai import OpenAI

from backend.paths import PROJECT_ROOT

_log = logging.getLogger("brainrot.pipeline")


def _pipe_print(msg: str) -> None:
    print(f"[brainrot.pipeline] {msg}", flush=True)
    _log.info(msg)


FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

# LLM + Whisper: OpenAI-compatible API (Dedalus or OpenAI).
DEFAULT_OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.dedaluslabs.ai/v1")

# OpenAI-compatible Kokoro HTTP server (same shape as test.py PAYLOAD).
DEFAULT_KOKORO_BASE_URL = os.environ.get("KOKORO_BASE_URL", "https://api.kokoro.dok.inkyg.com/v1")

# Always merged with GET /v1/models on KOKORO_BASE_URL (any OpenAI-compatible host).
TTS_MODELS = ["kokoro"]

# Kokoro voice ids (subset); blend strings like bm_george*0.7+af_bella*0.3 are supported if the server
# implements them. Merged with OpenAI presets + /voices + /models discovery.
TTS_VOICES = [
    "am_michael",
    "bm_george",
    "bm_george*0.7+af_bella*0.3",
    "af_bella",
    "af_sarah",
    "af_nova",
    "bm_fable",
    "bm_daniel",
    "bm_lewis",
    "bm_v0george",
    "am_echo",
    "am_onyx",
]

_OPTIONS_CACHE: dict[str, Any] | None = None
_OPTIONS_CACHE_MONO: float = 0.0
_OPTIONS_CACHE_TTL_S = 120.0


def get_llm_client() -> OpenAI:
    """Chat completions on an OpenAI-compatible API (OPENAI_API_KEY, OPENAI_BASE_URL)."""
    base = os.environ.get("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).rstrip("/")
    return OpenAI(base_url=base)


def get_tts_client() -> OpenAI:
    """Speech on the Kokoro OpenAI-compatible server."""
    base = os.environ.get("KOKORO_BASE_URL", DEFAULT_KOKORO_BASE_URL).rstrip("/")
    key = os.environ.get("KOKORO_API_KEY", "not-needed")
    return OpenAI(base_url=base, api_key=key)


def _http_list_all_model_ids(base_url: str, api_key: str, timeout: float = 60.0) -> list[str]:
    """GET {base}/models — same resource as `curl https://api.openai.com/v1/models` (OpenAI-compatible)."""
    base = (base_url or "").strip().rstrip("/")
    key = (api_key or "").strip()
    url = f"{base}/models"
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": "stewie-peter-ai-reel-maker/1.0",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:800]
        except Exception:
            pass
        _log.warning("GET %s → HTTP %s %s %s", url, e.code, e.reason, err_body)
        return []
    except Exception as e:
        _log.warning("GET %s failed: %s", url, e)
        return []
    try:
        text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
        j = json.loads(text)
    except json.JSONDecodeError as e:
        _log.warning("GET %s invalid JSON: %s", url, e)
        return []
    rows = j.get("data")
    if not isinstance(rows, list):
        alt = j.get("models")
        rows = alt if isinstance(alt, list) else []
    out: set[str] = set()
    for item in rows:
        if isinstance(item, dict):
            mid = item.get("id")
            if mid:
                out.add(str(mid))
        elif isinstance(item, str) and item.strip():
            out.add(item.strip())
    return sorted(out)


def _is_non_llm_chat_model(model_id: str) -> bool:
    """Exclude embeddings, audio-only, image, moderation, legacy completion, etc."""
    x = model_id.lower()
    if x.endswith("-tts") or x.endswith("_tts"):
        return True
    if x.startswith(("ada-", "babbage", "curie-", "davinci")):
        return True
    needles = (
        "embedding",
        "text-embedding",
        "whisper",
        "tts-",
        "dall-e",
        "dalle",
        "moderation",
        "text-search",
        "code-search",
        "gpt-image",
        "image-generation",
        "audio-transcribe",
        "omni-moderation",
        "realtime",
        "transcribe",
    )
    return any(n in x for n in needles)


def _is_tts_model_id(model_id: str) -> bool:
    x = model_id.lower()
    if x in ("kokoro", "tts-1", "tts-1-hd"):
        return True
    if "text-to-speech" in x or "text_to_speech" in x:
        return True
    if "tts" in x and "whisper" not in x:
        return True
    return False


def _kokoro_voice_like_ids(model_ids: list[str]) -> list[str]:
    """Kokoro-style voice ids sometimes appear as model ids (e.g. af_bella)."""
    pat = re.compile(r"^[a-z]{2}_[a-z0-9_]+$")
    return sorted({m for m in model_ids if pat.match(m)})


def _parse_voice_payload(payload: Any) -> list[str]:
    if isinstance(payload, list):
        if not payload:
            return []
        if isinstance(payload[0], str):
            return [str(x) for x in payload if isinstance(x, str)]
        if isinstance(payload[0], dict):
            out = []
            for x in payload:
                if not isinstance(x, dict):
                    continue
                v = x.get("id") or x.get("name") or x.get("voice")
                if v:
                    out.append(str(v))
            return out
    if isinstance(payload, dict):
        for k in ("data", "voices", "items", "voice_ids"):
            if k in payload:
                return _parse_voice_payload(payload[k])
    return []


def _try_fetch_kokoro_voice_ids() -> list[str]:
    """Optional JSON endpoints on the TTS host; comma-separated KOKORO_EXTRA_VOICES in .env."""
    b = os.environ.get("KOKORO_BASE_URL", DEFAULT_KOKORO_BASE_URL).rstrip("/")
    key = os.environ.get("KOKORO_API_KEY", "not-needed")
    manual = [x.strip() for x in (os.environ.get("KOKORO_EXTRA_VOICES") or "").split(",") if x.strip()]
    urls: list[str] = [f"{b}/voices", f"{b}/audio/voices"]
    if b.endswith("/v1"):
        urls.append(b[:-3] + "/voices")
    headers = {"Authorization": f"Bearer {key}"}
    found: list[str] = []
    for url in urls:
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                j = json.loads(resp.read())
            found.extend(_parse_voice_payload(j))
        except Exception:
            continue
    return manual + found


def get_dynamic_options() -> dict[str, Any]:
    """LLM ids from OPENAI_BASE_URL; TTS ids/voices = Kokoro seeds ∪ whatever /models and /voices return."""
    llm_base = os.environ.get("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).rstrip("/")
    tts_base = os.environ.get("KOKORO_BASE_URL", DEFAULT_KOKORO_BASE_URL).rstrip("/")
    llm_key = os.environ.get("OPENAI_API_KEY") or ""
    tts_key = os.environ.get("KOKORO_API_KEY", "not-needed")

    llm_ids = _http_list_all_model_ids(llm_base, llm_key)
    tts_ids = _http_list_all_model_ids(tts_base, tts_key)

    gpt_models = [m for m in llm_ids if not _is_non_llm_chat_model(m)]
    if not gpt_models and llm_ids:
        gpt_models = list(llm_ids)

    tts_models_fetched = [m for m in tts_ids if _is_tts_model_id(m)]
    if not tts_models_fetched and tts_ids:
        tts_models_fetched = list(tts_ids)
    tts_models = sorted(set(TTS_MODELS) | set(tts_models_fetched))

    voice_union = set(TTS_VOICES)
    voice_union.update(_try_fetch_kokoro_voice_ids())
    voice_union.update(_kokoro_voice_like_ids(tts_ids))
    tts_voices = sorted(voice_union)

    return {
        "gpt_models": gpt_models,
        "tts_models": tts_models,
        "tts_voices": tts_voices,
    }


def get_dynamic_options_cached() -> dict[str, Any]:
    global _OPTIONS_CACHE, _OPTIONS_CACHE_MONO
    now = time.monotonic()
    if _OPTIONS_CACHE is not None and (now - _OPTIONS_CACHE_MONO) < _OPTIONS_CACHE_TTL_S:
        return _OPTIONS_CACHE
    _OPTIONS_CACHE = get_dynamic_options()
    _OPTIONS_CACHE_MONO = now
    return _OPTIONS_CACHE


def get_default_gpt_model() -> str:
    m = get_dynamic_options_cached().get("gpt_models") or []
    return m[0] if m else "gpt-4o"


def get_default_tts_model() -> str:
    m = get_dynamic_options_cached().get("tts_models") or []
    if "kokoro" in m:
        return "kokoro"
    return m[0] if m else "kokoro"


def get_default_peter_voice() -> str:
    v = get_dynamic_options_cached().get("tts_voices") or []
    if "am_michael" in v:
        return "am_michael"
    return v[0] if v else "am_michael"


def get_default_stewie_voice() -> str:
    v = get_dynamic_options_cached().get("tts_voices") or []
    blend = "bm_george*0.7+af_bella*0.3"
    if blend in v:
        return blend
    if "bm_george" in v:
        return "bm_george"
    if len(v) > 1:
        return v[1]
    return v[0] if v else "bm_george"


def _primary_voice_id(voice: str) -> str:
    """kokoro blend 'bm_george*0.7+af_bella*0.3' -> 'bm_george' for single-voice fallback."""
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
        _pipe_print(f"TTS voice fallback {voice!r} → {primary!r} ({type(e).__name__})")
        tts_client.audio.speech.create(
            model=model,
            voice=primary,
            input=text,
            response_format="mp3",
        ).write_to_file(fp)

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


def _write_ass_subtitles_from_segments(ass_path: Path, segments: list[dict[str, Any]], cfg: Config) -> None:
    """Word-level timing from each dialogue line’s audio duration (no Whisper / transcription API)."""
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
    shake_speed: float = 10
    font_name: str = "Arial Black"
    font_size: int = 100
    text_color: str = "#FDE047"
    outline_color: str = "#000000"
    peter_voice: str = "am_michael"
    stewie_voice: str = "bm_george*0.7+af_bella*0.3"
    tts_model: str = "kokoro"
    gpt_model: str = "gpt-4o"
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
    _pipe_print(f"run_pipeline start bg={bg_path} out={output_path} temp_dir={temp_dir}")
    _ensure_ffmpeg()
    _pipe_print(f"ffmpeg bins: {FFMPEG_BIN!r} {FFPROBE_BIN!r} ({time.perf_counter() - t0:.2f}s)")
    temp_dir.mkdir(parents=True, exist_ok=True)

    dialogue = list(cfg.dialogue) if cfg.dialogue else []
    if not dialogue:
        if not (cfg.topic or "").strip():
            raise ValueError("Provide dialogue JSON or a topic (CLI auto-writes script).")
        _pipe_print("generating dialogue via LLM …")
        dialogue = generate_dialogue(llm_client, (cfg.topic or "").strip(), cfg.dialogue_lines, cfg.gpt_model)
        _pipe_print(f"LLM dialogue lines={len(dialogue)} ({time.perf_counter() - t0:.2f}s)")
    else:
        _pipe_print(f"using provided dialogue lines={len(dialogue)}")

    voices = {"Peter": cfg.peter_voice, "Stewie": cfg.stewie_voice}
    segments = []
    for i, line in enumerate(dialogue):
        sp, txt = line["speaker"], line["text"]
        fp = temp_dir / f"line_{i}.mp3"
        _pipe_print(f"TTS line {i + 1}/{len(dialogue)} speaker={sp} …")
        kokoro_speech_to_file(
            tts_client,
            fp,
            cfg.tts_model,
            voices.get(sp, "bm_george"),
            txt,
        )
        segments.append({"file": fp, "speaker": sp, "duration": _get_duration(fp), "text": txt})
    _pipe_print(f"TTS done ({time.perf_counter() - t0:.2f}s)")

    list_f = temp_dir / "concat.txt"
    list_f.write_text("\n".join(f"file '{s['file'].name}'" for s in segments))
    combined = temp_dir / "dialogue.mp3"
    _pipe_print("ffmpeg concat audio …")
    subprocess.run([FFMPEG_BIN, "-y", "-f", "concat", "-safe", "0", "-i", str(list_f), "-c", "copy", str(combined)],
                  check=True, capture_output=True)

    if cfg.tts_speed != 1.0:
        sped = temp_dir / "dialogue_sped.mp3"
        _pipe_print(f"ffmpeg atempo={cfg.tts_speed} …")
        subprocess.run([FFMPEG_BIN, "-y", "-i", str(combined), "-filter:a", f"atempo={cfg.tts_speed}", str(sped)],
                      check=True, capture_output=True)
        combined = sped

    timings, total = [], 0.0
    for s in segments:
        d = s["duration"] / cfg.tts_speed if cfg.tts_speed != 1.0 else s["duration"]
        timings.append({"speaker": s["speaker"], "start": total, "end": total + d})
        total += d

    ass = temp_dir / "subs.ass"
    _pipe_print(f"ASS subtitles from TTS segments (no Whisper) total_duration≈{total:.2f}s …")
    _write_ass_subtitles_from_segments(ass, segments, cfg)
    _pipe_print(f"ASS done ({time.perf_counter() - t0:.2f}s)")

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
    # Audio: TTS dialogue only (background video is silent — no mix with [0:a]).
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
    _pipe_print(
        f"final ffmpeg mux (-t {total:.2f}s) bg={bg_path} → {out} "
        f"[libx264 preset=fast can take a long time on large bg videos] …"
    )
    subprocess.run([FFMPEG_BIN, "-y", "-stream_loop", "-1", "-i", str(bg_path), "-i", str(_overlay_png(root, "peter.png")), "-i", str(_overlay_png(root, "stewie.png")), "-i", str(combined),
                    "-filter_complex", fc, "-map", "[v_out]", "-map", "[a_out]",
                    "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-t", str(total), str(out)],
                   check=True, capture_output=True)
    try:
        out_sz = out.stat().st_size
    except OSError:
        out_sz = -1
    _pipe_print(f"run_pipeline complete output_bytes={out_sz} total_s={time.perf_counter() - t0:.2f}")
    return out
