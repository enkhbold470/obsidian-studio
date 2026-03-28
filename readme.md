# brainrot video generator

CLI-only: AI-written Peter vs Stewie dialogue, TTS, FFmpeg overlays on your background video. No web server.

## Setup

1. Copy **`core/.env.example`** to **`.env`** at the repository root and set **`OPENAI_API_KEY`** (and any provider URLs you use).
2. Put **`peter.png`** / **`stewie.png`** under the repo root, **`assets/`**, or **`core/assets/`**.

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

- **`core/`** — `brainrot.py` (pipeline), `cli.py`, `paths.py`, **`assets/`**
- **`temp_build/`** — scratch (git-ignored)
- **`docs/`** — extra notes

## License

MIT.
