# Character overlays

Place **`peter.png`** and **`stewie.png`** here (or at the repository root). The pipeline searches the root first, then this folder.

Docker builds copy this directory into the image — without the PNGs, video generation fails at the FFmpeg step with a clear missing-file error.
