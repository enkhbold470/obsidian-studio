# Vite build → Flask + static SPA. Runtime needs: backend, db migrations, assets, ffmpeg.
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
COPY db ./db
COPY assets ./assets

RUN mkdir -p storage/public storage/uploads temp_build

COPY --from=frontend /build/frontend/dist ./frontend/dist

ENV PORT=5001
ENV PYTHONUNBUFFERED=1
EXPOSE 5001

CMD ["python", "-m", "backend.main"]
