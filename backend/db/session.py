"""Engine and session factory."""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.url import sqlalchemy_url_from_database_url


def _dsn() -> str:
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        raise RuntimeError("DATABASE_URL is required (PostgreSQL connection string).")
    return dsn


def get_engine():
    url = sqlalchemy_url_from_database_url(_dsn())
    return create_engine(url, pool_pre_ping=True)


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

__all__ = ["engine", "SessionLocal", "get_engine"]
