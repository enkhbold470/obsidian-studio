"""MOSS-TTSD: multi-speaker dialogue TTS (Python API).

See docs/MOSS_API_MULTI_DIALOGUE_TTS.md — POST /api/v1/audio/speech with [S1]/[S2] tags.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

_log = logging.getLogger("moss.ttsd")

DEFAULT_MOSS_BASE_URL = os.environ.get("MOSS_BASE_URL", "https://studio.mosi.cn").rstrip("/")
DEFAULT_MOSS_MODEL = os.environ.get("MOSS_TTSD_MODEL", "moss-ttsd").strip() or "moss-ttsd"
# Raised so a typical 8-line brainrot dialogue (~800 tagged chars) goes as ONE request.
# Chunking causes separate TTSD calls whose WAV outputs concatenate badly.
DEFAULT_MAX_TAGGED_CHARS = int(os.environ.get("MOSS_TTSD_MAX_TAGGED_CHARS", "5000"))


def dialogue_lines_to_tagged_text(
    lines: list[dict[str, str]],
    *,
    speaker_s1: str = "Peter",
    speaker_s2: str = "Inky",
) -> str:
    """Build MOSS TTSD text: [S1]...[S2]... with no space after tags."""
    parts: list[str] = []
    tag_map = {speaker_s1: "[S1]", speaker_s2: "[S2]"}
    for line in lines:
        sp = line.get("speaker", "")
        txt = str(line.get("text", "") or "").strip()
        if not txt:
            continue
        tag = tag_map.get(sp)
        if tag is None:
            raise ValueError(f"Unknown speaker {sp!r}; expected {speaker_s1!r} or {speaker_s2!r}")
        parts.append(f"{tag}{txt}")
    return "".join(parts)


def chunk_dialogue_lines(
    lines: list[dict[str, str]],
    *,
    speaker_s1: str = "Peter",
    speaker_s2: str = "Inky",
    max_tagged_chars: int = DEFAULT_MAX_TAGGED_CHARS,
) -> list[list[dict[str, str]]]:
    """Split dialogue into batches so each batch's tagged string length stays under the limit."""
    lim = max(32, max_tagged_chars)
    chunks: list[list[dict[str, str]]] = []
    current: list[dict[str, str]] = []
    current_len = 0

    for line in lines:
        sp = line.get("speaker", "")
        txt = str(line.get("text", "") or "").strip()
        if not txt:
            continue
        if sp not in (speaker_s1, speaker_s2):
            raise ValueError(f"Unknown speaker {sp!r}; expected {speaker_s1!r} or {speaker_s2!r}")
        tag = "[S1]" if sp == speaker_s1 else "[S2]"
        piece_len = len(tag) + len(txt)
        if current and current_len + piece_len > lim:
            chunks.append(current)
            current = []
            current_len = 0
        current.append({"speaker": sp, "text": txt})
        current_len += piece_len

    if current:
        chunks.append(current)
    return chunks


def moss_ttsd_request_wav(
    tagged_text: str,
    *,
    voice_id: str,
    voice_id2: str,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout_s: float = 180.0,
    max_retries: int = 4,
) -> bytes:
    """Call MOSS TTSD once; return raw WAV bytes."""
    max_retries = max(1, max_retries)
    key = (api_key or os.environ.get("MOSS_API_KEY") or "").strip()
    if not key:
        raise ValueError("MOSS_API_KEY is not set.")

    base = (base_url or os.environ.get("MOSS_BASE_URL") or DEFAULT_MOSS_BASE_URL).rstrip("/")
    m = (model or os.environ.get("MOSS_TTSD_MODEL") or DEFAULT_MOSS_MODEL).strip() or DEFAULT_MOSS_MODEL

    url = f"{base}/api/v1/audio/speech"
    # Scale max_new_tokens to text length: ~4 audio tokens per input char is generous headroom.
    # Hardcoding 20000 caused TTSD to generate 400+ seconds of audio for short dialogues.
    n_chars = len((tagged_text or "").strip())
    max_new_tokens = min(3000, max(256, n_chars * 4))
    _log.info("TTSD request: model=%s chars=%d max_new_tokens=%d", m, n_chars, max_new_tokens)
    payload: dict[str, Any] = {
        "model": m,
        "text": tagged_text,
        "voice_id": voice_id.strip(),
        "voice_id2": voice_id2.strip(),
        "sampling_params": {
            "max_new_tokens": max_new_tokens,
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 50,
            # Suppress blank / silence tokens; prevents runaway audio generation.
            "audio_presence_penalty": 1.5,
        },
        "meta_info": False,
    }

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    delay = 2.0

    for attempt in range(max_retries):
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout_s)
        if resp.status_code in (429, 502, 503) and attempt < max_retries - 1:
            _log.warning(
                "MOSS TTSD HTTP %s — retry in %.1fs (attempt %s)",
                resp.status_code,
                delay,
                attempt + 1,
            )
            time.sleep(delay)
            delay = min(delay * 1.5, 30.0)
            continue
        resp.raise_for_status()
        data = resp.json()
        b64 = data.get("audio_data")
        if not isinstance(b64, str) or not b64:
            raise ValueError("MOSS response missing audio_data")
        return base64.b64decode(b64)


def synthesize_dialogue_wav(
    lines: list[dict[str, str]],
    *,
    voice_id: str,
    voice_id2: str,
    speaker_s1: str = "Peter",
    speaker_s2: str = "Inky",
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    max_tagged_chars: int = DEFAULT_MAX_TAGGED_CHARS,
    ffmpeg_bin: str = "ffmpeg",
    temp_dir: Path | None = None,
) -> bytes:
    """
    Full dialogue → WAV bytes. Splits into multiple MOSS requests when tagged text exceeds the limit,
    then concatenates WAVs with FFmpeg (copy).
    """
    chunks = chunk_dialogue_lines(
        lines,
        speaker_s1=speaker_s1,
        speaker_s2=speaker_s2,
        max_tagged_chars=max_tagged_chars,
    )
    if not chunks or all(not c for c in chunks):
        raise ValueError("No dialogue lines to synthesize.")

    wav_parts: list[bytes] = []
    for batch in chunks:
        tagged = dialogue_lines_to_tagged_text(
            batch, speaker_s1=speaker_s1, speaker_s2=speaker_s2
        )
        if not tagged.strip():
            continue
        wav_parts.append(
            moss_ttsd_request_wav(
                tagged,
                voice_id=voice_id,
                voice_id2=voice_id2,
                api_key=api_key,
                base_url=base_url,
                model=model,
            )
        )

    if not wav_parts:
        raise ValueError("MOSS produced no audio.")

    if len(wav_parts) == 1:
        return wav_parts[0]

    if temp_dir is None:
        raise ValueError("temp_dir is required when dialogue is split into multiple MOSS chunks.")

    temp_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, raw in enumerate(wav_parts):
        p = temp_dir / f"moss_chunk_{i}.wav"
        p.write_bytes(raw)
        paths.append(p)

    out = temp_dir / "moss_dialogue.wav"
    concat_wav_files(paths, out, ffmpeg_bin=ffmpeg_bin)
    return out.read_bytes()


def concat_wav_files(paths: list[Path], out_path: Path, *, ffmpeg_bin: str = "ffmpeg") -> None:
    """Concatenate WAV files with identical format using FFmpeg stream copy."""
    if not paths:
        raise ValueError("No WAV paths to concat.")
    if len(paths) == 1:
        shutil.copyfile(paths[0], out_path)
        return

    td = out_path.parent
    lst = td / "moss_concat_list.txt"
    lines = "\n".join(f"file '{p.resolve()}'" for p in paths)
    lst.write_text(lines, encoding="utf-8")

    subprocess.run(
        [
            ffmpeg_bin,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )


def segment_durations_proportional(
    lines: list[dict[str, str]],
    total_duration: float,
) -> list[float]:
    """Split total audio duration across lines by character count (min weight 1 per line)."""
    weights: list[int] = []
    for line in lines:
        txt = str(line.get("text", "") or "").strip()
        weights.append(max(1, len(txt)))
    s = sum(weights)
    if s <= 0:
        return [total_duration / max(1, len(lines))] * len(lines)
    return [total_duration * w / s for w in weights]
