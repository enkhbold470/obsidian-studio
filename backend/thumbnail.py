"""JPEG thumbnail extraction from video (ffmpeg)."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

_log = logging.getLogger("brainrot.thumbnail")


def thumb_key_for_video_key(video_key: str) -> str:
    """S3 key for JPEG thumbnail next to the video object (e.g. foo.mp4 → foo.thumb.jpg)."""
    return str(Path(video_key).with_suffix(".thumb.jpg"))


def extract_video_thumbnail_jpg(video_path: Path, dest_jpg: Path, *, seek_s: float = 1.0) -> bool:
    """Extract one frame to JPEG. Returns False on failure (non-fatal for callers)."""
    dest_jpg.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(seek_s),
                "-i",
                str(video_path),
                "-vframes",
                "1",
                "-q:v",
                "3",
                str(dest_jpg),
            ],
            capture_output=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        _log.warning("ffmpeg thumbnail: %s", e)
        return False
    if r.returncode != 0:
        _log.warning(
            "ffmpeg thumbnail failed rc=%s stderr=%s",
            r.returncode,
            (r.stderr or b"")[:500],
        )
        return False
    try:
        return dest_jpg.is_file() and dest_jpg.stat().st_size > 0
    except OSError:
        return False
