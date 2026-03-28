# brainrot video generator

CLI-only: AI-written Peter vs Inky dialogue, MOSS TTSD, FFmpeg overlays on your background video. No web server.

## Setup

1. Copy **`core/.env.example`** to **`.env`** at the repository root and set **`OPENAI_API_KEY`**, **`MOSS_API_KEY`**, **`VOICE_ID_PETER`** ([S1]) and **`VOICE_ID_INKY`** ([S2]). See **`docs/MOSS_API_MULTI_DIALOGUE_TTS.md`**. Optional: **`MOSS_USE_SINGLE_VOICE_FOR_ALL=1`** plus **`MOSS_SINGLE_VOICE_ID`** to force one voice for both speakers.
2. Put **`peter.png`** / **`inky.png`** under the repo root, **`assets/`**, or **`core/assets/`**.

```bash
uv sync
```

## Run

```bash
uv run brainrot --topic "pineapple on pizza" --bg /path/to/vertical.mp4 --output out.mp4
```

Or:

```bash
uv run python -m core.cli --topic "..." --bg /path/to/bg.mp4 [--lines 8] [--speed 1.2] [--shake 15]
```

## Layout

- **`core/`** — `brainrot.py` (pipeline), `moss_ttsd.py` (MOSS-TTSD), `moss_tts.py` (optional single-speaker smoke test), `cli.py`, `paths.py`, **`assets/`**
- **`temp_build/`** — scratch (git-ignored)
- **`docs/`** — extra notes

## License

MIT.
