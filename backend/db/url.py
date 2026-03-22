"""Normalize DATABASE_URL for SQLAlchemy + psycopg3."""
from __future__ import annotations


def sqlalchemy_url_from_database_url(dsn: str) -> str:
    dsn = dsn.strip()
    if not dsn:
        return dsn
    if dsn.startswith("postgresql+psycopg"):
        return dsn
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn[len("postgresql://") :]
    return dsn
