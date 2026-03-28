"""MOSS-TTS: single-speaker speech synthesis (Python API).

See docs/MOSS-TTS_regular.md — POST /api/v1/audio/speech with model moss-tts, one voice_id per request.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any

import requests

_log = logging.getLogger("moss.tts")

DEFAULT_MOSS_BASE_URL = os.environ.get("MOSS_BASE_URL", "https://studio.mosi.cn").rstrip("/")
DEFAULT_MOSS_TTS_MODEL = os.environ.get("MOSS_TTS_MODEL", "moss-tts").strip() or "moss-tts"


def expected_duration_hint_sec(text: str) -> float | None:
    """Optional MOSS hint: ~0.5–1.5× normal reading time (doc best practice)."""
    t = (text or "").strip()
    if not t:
        return None
    words = max(1, len(t.split()))
    sec = words * 0.35
    return max(0.8, min(120.0, sec))


def moss_tts_request_wav(
    text: str,
    *,
    voice_id: str,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout_s: float = 300.0,
    max_retries: int = 4,
) -> bytes:
    """Call MOSS-TTS once; return raw WAV bytes (24 kHz per docs)."""
    max_retries = max(1, max_retries)
    key = (api_key or os.environ.get("MOSS_API_KEY") or "").strip()
    if not key:
        raise ValueError("MOSS_API_KEY is not set.")

    base = (base_url or os.environ.get("MOSS_BASE_URL") or DEFAULT_MOSS_BASE_URL).rstrip("/")
    m = (model or os.environ.get("MOSS_TTS_MODEL") or DEFAULT_MOSS_TTS_MODEL).strip() or DEFAULT_MOSS_TTS_MODEL

    url = f"{base}/api/v1/audio/speech"
    tid = (text or "").strip()
    if not tid:
        raise ValueError("TTS text is empty.")

    exp = expected_duration_hint_sec(tid)
    payload: dict[str, Any] = {
        "model": m,
        "text": tid,
        "voice_id": voice_id.strip(),
        "meta_info": False,
        "sampling_params": {
            "max_new_tokens": 512,
            "temperature": 1.5,
            "top_p": 0.8,
            "top_k": 50,
        },
    }
    if exp is not None:
        payload["expected_duration_sec"] = round(exp, 2)

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    delay = 2.0

    for attempt in range(max_retries):
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout_s)
        if resp.status_code in (429, 502, 503) and attempt < max_retries - 1:
            _log.warning(
                "MOSS TTS HTTP %s — retry in %.1fs (attempt %s)",
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
