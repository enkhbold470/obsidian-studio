"""Postgres user store + generation history (schema from db/schema.ts via Drizzle migrations)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg
import psycopg.errors
from psycopg.rows import dict_row
from psycopg.types.json import Json
from werkzeug.security import check_password_hash, generate_password_hash

from backend.migrate import apply_sql_migrations
from backend.paths import PROJECT_ROOT


def _dsn() -> str:
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        raise RuntimeError("DATABASE_URL is required (PostgreSQL connection string).")
    return dsn


@dataclass
class User:
    id: int
    email: str
    gallery_public: bool = False


@dataclass
class UserBackground:
    id: str
    user_id: int
    storage_key: str
    original_filename: str
    created_at: datetime


@dataclass
class Generation:
    id: str
    user_id: int | None
    job_uid: str
    output_key: str
    output_format: str
    topic: str | None
    dialogue: list[dict[str, Any]]
    bg_source: str | None
    created_at: datetime


def init_db() -> None:
    with psycopg.connect(_dsn()) as conn:
        apply_sql_migrations(conn)


def create_user(email: str, password: str) -> User | None:
    email = email.strip().lower()
    if "@" not in email or len(password) < 8:
        return None
    ph = generate_password_hash(password)
    now = datetime.now(timezone.utc)
    with psycopg.connect(_dsn()) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, created_at)
                    VALUES (%s, %s, %s)
                    RETURNING id, email
                    """,
                    (email, ph, now),
                )
                row = cur.fetchone()
            conn.commit()
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            return None
    if not row:
        return None
    return User(id=row[0], email=row[1], gallery_public=False)


def verify_user(email: str, password: str) -> User | None:
    email = email.strip().lower()
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, gallery_public FROM users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()
    if not row or not check_password_hash(row[2], password):
        return None
    return User(id=row[0], email=row[1], gallery_public=bool(row[3]))


def get_user_by_id(user_id: int) -> User | None:
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, gallery_public FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
    return User(id=row[0], email=row[1], gallery_public=bool(row[2])) if row else None


def set_user_gallery_public(user_id: int, public: bool) -> None:
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET gallery_public = %s WHERE id = %s",
                (public, user_id),
            )
        conn.commit()


def insert_user_background_record(
    bg_id: str,
    user_id: int,
    storage_key: str,
    original_filename: str,
) -> None:
    now = datetime.now(timezone.utc)
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_backgrounds (id, user_id, storage_key, original_filename, created_at)
                VALUES (%s::uuid, %s, %s, %s, %s)
                """,
                (bg_id, user_id, storage_key, original_filename, now),
            )
        conn.commit()


def list_user_backgrounds(user_id: int) -> list[UserBackground]:
    with psycopg.connect(_dsn(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, user_id, storage_key, original_filename, created_at
                FROM user_backgrounds WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
    return [
        UserBackground(
            id=r["id"],
            user_id=r["user_id"],
            storage_key=r["storage_key"],
            original_filename=r["original_filename"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def get_user_background(user_id: int, bg_id: str) -> UserBackground | None:
    with psycopg.connect(_dsn(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, user_id, storage_key, original_filename, created_at
                FROM user_backgrounds WHERE user_id = %s AND id = %s::uuid
                """,
                (user_id, bg_id),
            )
            row = cur.fetchone()
    if not row:
        return None
    return UserBackground(
        id=row["id"],
        user_id=row["user_id"],
        storage_key=row["storage_key"],
        original_filename=row["original_filename"],
        created_at=row["created_at"],
    )


def delete_user_background(user_id: int, bg_id: str) -> bool:
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_backgrounds WHERE user_id = %s AND id = %s::uuid RETURNING id",
                (user_id, bg_id),
            )
            row = cur.fetchone()
        conn.commit()
    return bool(row)


def insert_generation(
    *,
    user_id: int | None,
    job_uid: str,
    output_key: str,
    output_format: str,
    topic: str,
    dialogue: list[dict[str, Any]],
    bg_source: str | None,
) -> None:
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO generations (
                    user_id, job_uid, output_key, output_format, topic, dialogue, bg_source, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    job_uid,
                    output_key,
                    output_format,
                    topic or None,
                    Json(dialogue),
                    bg_source,
                    datetime.now(timezone.utc),
                ),
            )
        conn.commit()


def get_generation_by_job_uid(job_uid: str) -> Generation | None:
    with psycopg.connect(_dsn(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, user_id, job_uid, output_key, output_format,
                       topic, dialogue, bg_source, created_at
                FROM generations WHERE job_uid = %s
                """,
                (job_uid,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return Generation(
        id=row["id"],
        user_id=row["user_id"],
        job_uid=row["job_uid"],
        output_key=row["output_key"],
        output_format=row["output_format"],
        topic=row["topic"],
        dialogue=row["dialogue"] if isinstance(row["dialogue"], list) else [],
        bg_source=row["bg_source"],
        created_at=row["created_at"],
    )


def list_generations_for_user(user_id: int, limit: int = 50) -> list[Generation]:
    with psycopg.connect(_dsn(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, user_id, job_uid, output_key, output_format,
                       topic, dialogue, bg_source, created_at
                FROM generations
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()
    out: list[Generation] = []
    for row in rows:
        out.append(
            Generation(
                id=row["id"],
                user_id=row["user_id"],
                job_uid=row["job_uid"],
                output_key=row["output_key"],
                output_format=row["output_format"],
                topic=row["topic"],
                dialogue=row["dialogue"] if isinstance(row["dialogue"], list) else [],
                bg_source=row["bg_source"],
                created_at=row["created_at"],
            )
        )
    return out
