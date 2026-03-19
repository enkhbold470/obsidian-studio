# Public video library

Drop **9:16** background videos here (`.mp4`, `.mov`, `.mkv`, `.webb`). The web UI lists these as selectable backgrounds alongside file uploads.

Uploaded videos during a session are stored under `storage/uploads/` instead.

For local development, symlink a large file if you prefer not to duplicate:

```bash
ln -sf /path/to/minecraft_parkour1.mp4 ./minecraft_parkour1.mp4
```

Large binaries are intentionally ignored by Git via `.dockerignore` / `.gitignore` patterns where applicable; keep originals elsewhere and mount or copy them on the server.
