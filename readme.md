# brainrot video generator

Generate vertical “brainrot” debate clips: AI-written Peter vs Stewie dialogue, OpenAI TTS + Whisper timings, FFmpeg overlays + subtitles on your background footage.

## Repo layout

- **`backend/`** — Flask API, Postgres auth, video pipeline (`brainrot.py`), Alembic, Python deps (`requirements.txt`), CLI (`cli.py`), character **`assets/`**.
- **`frontend/`** — Vite + React + Tailwind UI.
- **`storage/public/`** — list of bundled background videos for the UI.
- **`storage/uploads/`** — per-request uploads (git-ignored).
- **`docs/`** — architecture, local dev, **Dokploy** deploy, optional scale-up notes (`OPERATIONS.md`).
- **Root** — `Dockerfile`, `docker-compose.yml`, `readme.md`, `license` (minimal).

## Quick start (web)

1. Copy `backend/.env.example` to **`.env` at the repository root** and set `OPENAI_API_KEY` and a strong `SECRET_KEY`.
2. Add character PNGs under **`backend/assets/`** or the repo root.
3. Put background videos in **`storage/public/`** (e.g. 9:16 `.mp4`).
4. Install backend deps and run API: see **`docs/DEVELOPMENT.md`**.
5. In another terminal: `cd frontend && bun install && bun run dev` → open the printed local URL.

Production options: (1) build the frontend (`cd frontend && bun run build`) and run `python -m backend.main` with `frontend/dist` present to serve UI + `/api/*`; or (2) deploy the **API Docker image** and host the SPA separately — set `VITE_API_BASE_URL` and backend `CORS_ORIGINS` (see **`docs/DEPLOY_DOKPLOY.md`**).

## CLI

```bash
uv run python -m backend.cli --topic "pineapple on pizza" --bg /path/to/video.mp4 [--lines 8] [--speed 1.2] [--shake 15]
```

## Deploy

See **`docs/DEPLOY_DOKPLOY.md`** for Docker + Dokploy (ports, env, volumes).

## License

MIT.
