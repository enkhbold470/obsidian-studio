"""Apply Alembic migrations to HEAD."""
from __future__ import annotations

import os

from alembic import command
from alembic.config import Config

from backend.db.url import sqlalchemy_url_from_database_url
from backend.paths import BACKEND_ROOT


def _dsn() -> str:
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        raise RuntimeError("DATABASE_URL is required (PostgreSQL connection string).")
    return dsn


def apply_alembic_migrations() -> None:
    alembic_ini = BACKEND_ROOT / "alembic.ini"
    if not alembic_ini.is_file():
        raise FileNotFoundError(f"Missing {alembic_ini}")
    cfg = Config(str(alembic_ini))
    url = sqlalchemy_url_from_database_url(_dsn())
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
