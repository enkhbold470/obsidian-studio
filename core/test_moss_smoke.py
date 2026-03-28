"""MOSS-TTSD smoke test — same API as the brainrot pipeline (dialogue + [S1]/[S2]).

See docs/MOSS_API_MULTI_DIALOGUE_TTS.md. Requires MOSS_API_KEY and both voice IDs.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

import requests
from dotenv import load_dotenv

from core.moss_ttsd import dialogue_lines_to_tagged_text, moss_ttsd_request_wav
from core.paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

# Short two-turn dialogue — must use Peter / Inky so tags map to [S1] / [S2].
DIALOGUE = [
    {"speaker": "Peter", "text": "Hey Inky, pineapple belongs on pizza."},
    {"speaker": "Inky", "text": "Blast! That is objectively wrong."},
]

OUTPUT_PATH = Path("moss_ttsd_smoke.wav")


def main() -> None:
    key = os.environ.get("MOSS_API_KEY", "").strip()
    peter = os.environ.get("VOICE_ID_PETER", "").strip()
    inky = os.environ.get("VOICE_ID_INKY", "").strip()
    if not key:
        raise SystemExit("Set MOSS_API_KEY in .env")
    if not peter or not inky:
        raise SystemExit(
            "Set VOICE_ID_PETER and VOICE_ID_INKY in .env "
            "(MOSS-TTSD maps voice_id → [S1] Peter, voice_id2 → [S2] Inky)."
        )

    tagged = dialogue_lines_to_tagged_text(DIALOGUE)
    print(f"Tagged text ({len(tagged)} chars): {tagged!r}")
    print(f"voice_id ([S1] Peter): {peter!r}")
    print(f"voice_id2 ([S2] Inky): {inky!r}")

    try:
        wav = moss_ttsd_request_wav(tagged, voice_id=peter, voice_id2=inky)
    except requests.HTTPError as e:
        print(f"MOSS HTTP error: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Status: {e.response.status_code}", file=sys.stderr)
            print(e.response.text[:8000], file=sys.stderr)
        raise SystemExit(1) from e
    except ValueError as e:
        print(f"MOSS response error: {e}", file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1) from e

    OUTPUT_PATH.write_bytes(wav)
    print(f"Wrote {OUTPUT_PATH.resolve()} ({len(wav)} bytes WAV)")


if __name__ == "__main__":
    main()
