# Backend API only (Flask + Alembic + ffmpeg). Build and host the SPA separately (e.g. Bun/Vite on Dokploy).
# Runtime needs: backend, Alembic, assets, ffmpeg — no frontend/dist in image.
FROM python:3.12-slim-bookworm
WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends ffmpeg \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend

RUN mkdir -p storage/public storage/uploads temp_build

ENV PORT=5001
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
EXPOSE 5001

# Uvicorn WSGI (Flask) — same as `python -m backend.main`
CMD ["python", "-m", "backend.main"]
