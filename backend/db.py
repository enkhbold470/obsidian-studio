"""SQLite user store — minimal, no ORM."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from backend.paths import DEFAULT_DB_PATH, INSTANCE_DIR


@dataclass
class User:
    id: int
    email: str


def get_connection() -> sqlite3.Connection:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DEFAULT_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_user(email: str, password: str) -> User | None:
    email = email.strip().lower()
    if "@" not in email or len(password) < 8:
        return None
    ph = generate_password_hash(password)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, ph, now),
        )
        conn.commit()
        row = conn.execute("SELECT id, email FROM users WHERE email = ?", (email,)).fetchone()
        return User(id=row["id"], email=row["email"]) if row else None
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def verify_user(email: str, password: str) -> User | None:
    email = email.strip().lower()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
        if not row or not check_password_hash(row["password_hash"], password):
            return None
        return User(id=row["id"], email=row["email"])
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> User | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
        return User(id=row["id"], email=row["email"]) if row else None
    finally:
        conn.close()
