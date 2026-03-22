# Local development

## Prerequisites

- Python 3.12+ with `uv` or `pip`
- Bun (or Node + npm) for the frontend
- PostgreSQL 16+ (local install or `docker compose up postgres` only)
- `OPENAI_API_KEY` in `.env` at the **repository root** (same level as `app.py`)

## Environment variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Required for script draft, TTS, Whisper. |
| `DATABASE_URL` | PostgreSQL connection string (required for the web API). |
| `SECRET_KEY` | Flask session signing (required in any shared or production environment). |
| `PORT` | HTTP port (default `5001`). |
| `CORS_ORIGINS` | Comma-separated list; default includes Vite dev URLs. |
| `SKIP_AUTH` | If `1` / `true` / `yes`, disables auth on protected API routes (local only). |
| `FLASK_DEBUG` | Set to `1` for Flask debug mode. |

## Backend

From the repo root (set `DATABASE_URL`, e.g. `postgresql://brainrot:brainrot@localhost:5432/brainrot`):

```bash
uv pip install -r requirements.txt
uv run python -m backend.main
```

Schema changes: edit SQLAlchemy models in `backend/db/models.py`, then `alembic revision --autogenerate -m "describe"` (or hand-write a revision), and apply with `alembic upgrade head` or rely on app startup (`init_db()` runs Alembic to `head`).

API: `http://127.0.0.1:5001/api/options`

Without a built frontend, opening `http://127.0.0.1:5001/` returns JSON explaining to run the frontend build.

## Frontend (Vite)

```bash
cd frontend && bun install && bun run dev
```

UI: `http://localhost:5173` — requests to `/api` are proxied to the Flask port.

Log in or register, or set `SKIP_AUTH=1` on the backend to bypass auth during iteration.

## One-off CLI render

```bash
uv run app.py --topic "your topic" --bg /path/to/bg.mp4 --output out.mp4
```

## Linting

- Frontend: `cd frontend && bun run build` (TypeScript + Vite compile check).
