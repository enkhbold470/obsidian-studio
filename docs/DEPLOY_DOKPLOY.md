# Running in production / automation

This project is **CLI-only**. There is no HTTP server to deploy.

- Run **`uv sync`** (or install from lockfile) on the machine that will render.
- Set environment variables from **`core/.env.example`** (especially **`OPENAI_API_KEY`**).
- Ensure **`ffmpeg`** / **`ffprobe`** are on `PATH` (or the pipeline can download macOS builds into `temp_build/ffmpeg_bin/` when ASS support is missing).
- Invoke **`uv run brainrot ...`** or **`uv run python -m core.cli ...`** from cron, a queue worker, or your own orchestration.

If you add a web or mobile app later, wrap this CLI (or import `run_pipeline`) from your own service.
