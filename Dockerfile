# Vite build → Flask + static SPA. Runtime needs: backend, Alembic, assets, ffmpeg.
FROM oven/bun:1 AS frontend
WORKDIR /build/frontend
COPY frontend/package.json ./
RUN bun install
COPY frontend/ ./
RUN bun run build

FROM python:3.12-slim-bookworm
WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends ffmpeg \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY alembic.ini .
COPY alembic ./alembic
COPY assets ./assets

RUN mkdir -p storage/public storage/uploads temp_build

COPY --from=frontend /build/frontend/dist ./frontend/dist

ENV PORT=5001
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
EXPOSE 5001

# Uvicorn WSGI (Flask) — same as `python -m backend.main`
CMD ["python", "-m", "backend.main"]
