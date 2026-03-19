"""Single source of truth for repo layout."""
from __future__ import annotations

from pathlib import Path

# backend/ -> repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent
STORAGE_PUBLIC = PROJECT_ROOT / "storage" / "public"
STORAGE_UPLOADS = PROJECT_ROOT / "storage" / "uploads"
INSTANCE_DIR = BACKEND_ROOT / "instance"
DEFAULT_DB_PATH = INSTANCE_DIR / "app.sqlite"
