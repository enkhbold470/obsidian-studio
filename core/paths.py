"""Single source of truth for repo layout."""
from __future__ import annotations

from pathlib import Path

# core/ -> repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORE_ROOT = Path(__file__).resolve().parent
STORAGE_PUBLIC = PROJECT_ROOT / "storage" / "public"
STORAGE_UPLOADS = PROJECT_ROOT / "storage" / "uploads"
INSTANCE_DIR = CORE_ROOT / "instance"
