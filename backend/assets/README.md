# Character overlays

Place **`peter.png`** and **`stewie.png`** here (or at the repository root). The pipeline checks the repo root, then `assets/` at the root, then this folder (`backend/assets/`).

Docker builds include this directory via `COPY backend` — without the PNGs, video generation fails at the FFmpeg step with a clear missing-file error.
