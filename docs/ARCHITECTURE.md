# Architecture

## Layout

| Path | Role |
|------|------|
| `backend/brainrot.py` | OpenAI dialogue/TTS/Whisper, FFmpeg pipeline, optional bundled FFmpeg download (macOS). |
| `backend/main.py` | Flask app: `/api/*` JSON + multipart, SQLite auth, SPA fallback from `frontend/dist`. |
| `backend/db.py` | SQLite users (`email`, `password_hash`) via `werkzeug.security`. |
| `backend/paths.py` | `PROJECT_ROOT`, `storage/public`, `storage/uploads`, DB path under `backend/instance/`. |
| `frontend/` | Vite + React + Tailwind. Dev server proxies `/api` → Flask (`5001`). |
| `storage/public/` | Read-only catalogue of bundled background videos for the UI. |
| `storage/uploads/` | Temporary user uploads (per-render). |
| `temp_build/` | Render working dirs, FFmpeg cache, rendered outputs (`outputs/`). |
| `app.py` | CLI wrapper around `run_pipeline` for non-web use. |
| `assets/` | `peter.png` / `stewie.png` (or same files at repo root — resolved automatically). |

## Auth

- Sessions are cookie-based (`Flask` `session`, keyed by `SECRET_KEY`).
- `SKIP_AUTH=1` (or `true`/`yes`) skips the login gate on script/generate/output endpoints — useful for CI or quick API tests; **do not enable in production**.
- Registration enforces password length ≥ 8 and a case-insensitive unique email.

## Data flow (web)

1. User drafts or edits dialogue in React (row editor → JSON in `FormData`).
2. `POST /api/generate` validates dialogue, resolves background (`storage/public` name or uploaded file), runs `run_pipeline`.
3. `GET /api/output/<id>` streams the resulting video (auth required unless `SKIP_AUTH`).

## Production static files

Flask serves the built SPA from `frontend/dist` for all non-`api` routes. Build the frontend before running the server (see `Dockerfile` or `docs/DEVELOPMENT.md`).

## Dependencies

- **Python**: `requirements.txt` (OpenAI SDK, Flask, flask-cors, python-dotenv).
- **Node**: managed in `frontend/package.json`; Bun is used in Docker and documented for local dev.
