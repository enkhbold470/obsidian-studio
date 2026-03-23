"""Postgres persistence via SQLAlchemy ORM."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from backend.db.models import Generation as GenRow
from backend.db.models import User as UserRow
from backend.db.models import UserBackground as BgRow
from backend.db.session import SessionLocal
from backend.migrate import apply_alembic_migrations


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
    elapsed_seconds: float | None
    render_meta: dict[str, Any] | None


def init_db() -> None:
    apply_alembic_migrations()


def _bg_from_row(r: BgRow) -> UserBackground:
    return UserBackground(
        id=str(r.id),
        user_id=r.user_id,
        storage_key=r.storage_key,
        original_filename=r.original_filename,
        created_at=r.created_at,
    )


def _gen_from_row(r: GenRow) -> Generation:
    d = r.dialogue if isinstance(r.dialogue, list) else []
    meta = r.render_meta if isinstance(getattr(r, "render_meta", None), dict) else None
    return Generation(
        id=str(r.id),
        user_id=r.user_id,
        job_uid=r.job_uid,
        output_key=r.output_key,
        output_format=r.output_format,
        topic=r.topic,
        dialogue=d,
        bg_source=r.bg_source,
        created_at=r.created_at,
        elapsed_seconds=getattr(r, "elapsed_seconds", None),
        render_meta=meta,
    )


def create_user(email: str, password: str) -> User | None:
    email = email.strip().lower()
    if "@" not in email or len(password) < 8:
        return None
    ph = generate_password_hash(password)
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        try:
            u = UserRow(email=email, password_hash=ph, created_at=now, gallery_public=False)
            session.add(u)
            session.commit()
            session.refresh(u)
            return User(id=u.id, email=u.email, gallery_public=bool(u.gallery_public))
        except IntegrityError:
            session.rollback()
            return None


def verify_user(email: str, password: str) -> User | None:
    email = email.strip().lower()
    with SessionLocal() as session:
        u = session.scalar(select(UserRow).where(UserRow.email == email))
        if not u or not check_password_hash(u.password_hash, password):
            return None
        return User(id=u.id, email=u.email, gallery_public=bool(u.gallery_public))


def get_user_by_id(user_id: int) -> User | None:
    with SessionLocal() as session:
        u = session.get(UserRow, user_id)
        if not u:
            return None
        return User(id=u.id, email=u.email, gallery_public=bool(u.gallery_public))


def set_user_gallery_public(user_id: int, public: bool) -> None:
    with SessionLocal() as session:
        session.execute(
            update(UserRow).where(UserRow.id == user_id).values(gallery_public=public)
        )
        session.commit()


def insert_user_background_record(
    bg_id: str,
    user_id: int,
    storage_key: str,
    original_filename: str,
) -> None:
    now = datetime.now(timezone.utc)
    uid = uuid.UUID(bg_id) if isinstance(bg_id, str) else bg_id
    with SessionLocal() as session:
        session.add(
            BgRow(
                id=uid,
                user_id=user_id,
                storage_key=storage_key,
                original_filename=original_filename,
                created_at=now,
            )
        )
        session.commit()


def list_user_backgrounds(user_id: int) -> list[UserBackground]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(BgRow)
            .where(BgRow.user_id == user_id)
            .order_by(BgRow.created_at.desc())
        ).all()
    return [_bg_from_row(r) for r in rows]


def get_user_background(user_id: int, bg_id: str) -> UserBackground | None:
    uid = uuid.UUID(bg_id)
    with SessionLocal() as session:
        r = session.scalar(
            select(BgRow).where(BgRow.user_id == user_id, BgRow.id == uid)
        )
    return _bg_from_row(r) if r else None


def delete_user_background(user_id: int, bg_id: str) -> bool:
    uid = uuid.UUID(bg_id)
    with SessionLocal() as session:
        res = session.execute(
            delete(BgRow).where(BgRow.user_id == user_id, BgRow.id == uid)
        )
        session.commit()
        return res.rowcount > 0


def insert_generation(
    *,
    user_id: int | None,
    job_uid: str,
    output_key: str,
    output_format: str,
    topic: str,
    dialogue: list[dict[str, Any]],
    bg_source: str | None,
    elapsed_seconds: float | None = None,
    render_meta: dict[str, Any] | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add(
            GenRow(
                user_id=user_id,
                job_uid=job_uid,
                output_key=output_key,
                output_format=output_format,
                topic=topic or None,
                dialogue=dialogue,
                bg_source=bg_source,
                created_at=now,
                elapsed_seconds=elapsed_seconds,
                render_meta=render_meta,
            )
        )
        session.commit()


def get_generation_by_job_uid(job_uid: str) -> Generation | None:
    with SessionLocal() as session:
        r = session.scalar(select(GenRow).where(GenRow.job_uid == job_uid))
    return _gen_from_row(r) if r else None


def list_generations_for_user(user_id: int, limit: int = 50) -> list[Generation]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(GenRow)
            .where(GenRow.user_id == user_id)
            .order_by(GenRow.created_at.desc())
            .limit(limit)
        ).all()
    return [_gen_from_row(r) for r in rows]
