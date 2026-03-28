# Character overlays

Place **`peter.png`** and **`stewie.png`** here (or at the repository root). The pipeline checks the repo root, then `assets/` at the root, then this folder (`core/assets/`).

Without the PNGs, video generation fails at the FFmpeg step with a clear missing-file error.
