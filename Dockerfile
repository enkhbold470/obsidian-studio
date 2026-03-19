# Single image: Vite build + Flask API + static SPA
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
COPY app.py ./
COPY docs ./docs
COPY docs_rules ./docs_rules
COPY storage ./storage
COPY assets ./assets

COPY --from=frontend /build/frontend/dist ./frontend/dist

ENV PORT=5001
ENV PYTHONUNBUFFERED=1

EXPOSE 5001

CMD ["python", "-m", "backend.main"]
