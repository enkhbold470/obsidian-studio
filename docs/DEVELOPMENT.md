# Local development

There is no HTTP server — use the **CLI** only.

## Environment

Copy **`core/.env.example`** to **`.env`** at the repository root.

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Required for LLM APIs used by the pipeline. |
| `OPENAI_BASE_URL` | Optional; OpenAI-compatible chat base URL. |
| `MOSS_API_KEY` | Required for MOSS-TTSD (`core/moss_ttsd.py`). |
| `VOICE_ID_PETER` / `VOICE_ID_INKY` | MOSS `voice_id` ([S1] Peter) and `voice_id2` ([S2] Inky). |
| `MOSS_USE_SINGLE_VOICE_FOR_ALL` | Set to `1` / `true` / `yes` to use `MOSS_SINGLE_VOICE_ID` for **both** speakers (opt-in; avoids accidental single-voice mode). |

See **`docs/MOSS_API_MULTI_DIALOGUE_TTS.md`** for the upstream TTSD API.

## Dependencies

From the repo root:

```bash
uv sync
```

## Run a render

Default: **verbose** step timings. Use **`--quiet`** for less output.

```bash
uv run brainrot --topic "your topic" --bg ./clip.mp4 --output ./out.mp4
```

Same options as `python -m core.cli` (`--lines`, `--speed`, `--shake`, `--single-voice-id`, etc.).

## MOSS-TTSD smoke test (same as pipeline)

With `MOSS_API_KEY`, `VOICE_ID_PETER`, and `VOICE_ID_INKY` in `.env`:

```bash
uv run python core/test_moss_smoke.py
```

Writes **`moss_ttsd_smoke.wav`**. See **`docs/MOSS_API_MULTI_DIALOGUE_TTS.md`**.

For regular single-speaker TTS (`moss-tts`), use **`docs/MOSS-TTS_regular.md`** and call `core/moss_tts.py` from a small script or REPL.
