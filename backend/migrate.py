"""Apply SQL migrations from db/migrations (Drizzle-compatible DDL)."""
from __future__ import annotations

import re
from pathlib import Path

from psycopg import Connection

from backend.paths import PROJECT_ROOT

MIGRATIONS_DIR = PROJECT_ROOT / "db" / "migrations"


def _split_sql_statements(sql: str) -> list[str]:
    """Split migration file on semicolons before CREATE / ALTER."""
    parts = re.split(r"\s*;\s*(?=(?:CREATE|ALTER)\s)", sql, flags=re.IGNORECASE | re.DOTALL)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if not p or p.startswith("--"):
            continue
        if not p.endswith(";"):
            p += ";"
        out.append(p)
    return out


def apply_sql_migrations(conn: Connection) -> None:
    if not MIGRATIONS_DIR.is_dir():
        raise FileNotFoundError(f"Migrations directory missing: {MIGRATIONS_DIR}")
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"No .sql files in {MIGRATIONS_DIR}")
    with conn.transaction():
        for path in files:
            sql = path.read_text(encoding="utf-8")
            for stmt in _split_sql_statements(sql):
                conn.execute(stmt)
