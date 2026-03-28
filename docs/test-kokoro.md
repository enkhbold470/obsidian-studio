"""Kokoro TTS smoke test — same OpenAI-compatible call as the brainrot pipeline."""

from pathlib import Path

from core.brainrot import get_tts_client, kokoro_speech_to_file

PAYLOAD = {
    "model": "kokoro",
    "input": "Blast! The time machine is broken again.",
    "voice": "bm_george*0.7+af_bella*0.3",
    "response_format": "mp3",
}

OUTPUT_PATH = "stewie_simulation.mp3"


def main() -> None:
    client = get_tts_client()
    kokoro_speech_to_file(
        client,
        Path(OUTPUT_PATH),
        PAYLOAD["model"],
        PAYLOAD["voice"],
        PAYLOAD["input"],
    )
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
