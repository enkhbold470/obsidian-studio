# brainrot video generator

Generate vertical “brainrot” debate clips: AI-written Peter vs Stewie dialogue, OpenAI TTS + Whisper timings, FFmpeg overlays + subtitles on your background footage.

## Repo layout

- **`backend/`** — Flask API, SQLite auth, video pipeline (`brainrot.py`).
- **`frontend/`** — Vite + React + Tailwind UI.
- **`storage/public/`** — list of bundled background videos for the UI.
- **`storage/uploads/`** — per-request uploads (git-ignored).
- **`assets/`** — `peter.png` / `stewie.png` (see `assets/README.md`).
- **`docs/`** — architecture, local dev, **Dokploy** deploy, optional scale-up notes (`OPERATIONS.md`).

## Quick start (web)

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY` and a strong `SECRET_KEY`.
2. Add character PNGs under **`assets/`** or the repo root.
3. Put background videos in **`storage/public/`** (e.g. 9:16 `.mp4`).
4. Install backend deps and run API: see **`docs/DEVELOPMENT.md`**.
5. In another terminal: `cd frontend && bun install && bun run dev` → open the printed local URL.

Production-like single server: build the frontend (`bun run build`), then `python -m backend.main` serves both UI and `/api/*`.

## CLI

```bash
uv run app.py --topic "pineapple on pizza" --bg /path/to/video.mp4 [--lines 8] [--speed 1.2] [--shake 15]
```

## Deploy

See **`docs/DEPLOY_DOKPLOY.md`** for Docker + Dokploy (ports, env, volumes).

## License

MIT.
