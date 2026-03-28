# Local development

There is no HTTP server — use the **CLI** only.

## Environment

Copy **`core/.env.example`** to **`.env`** at the repository root.

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Required for LLM + APIs used by the pipeline. |
| `OPENAI_BASE_URL` | Optional; OpenAI-compatible chat/Whisper base URL. |
| `KOKORO_BASE_URL` | Kokoro-compatible TTS server (see `core/brainrot.py`). |

## Dependencies

From the repo root:

```bash
uv sync
```

## Run a render

```bash
uv run brainrot --topic "your topic" --bg ./clip.mp4 --output ./out.mp4
```

Same options as `python -m core.cli` (`--lines`, `--speed`, `--shake`, etc.).
