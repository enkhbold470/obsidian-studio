"""SQLAlchemy 2.0 models — single source of truth for Postgres schema."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="users_email_unique"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
    gallery_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    backgrounds: Mapped[List["UserBackground"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    generations: Mapped[List["Generation"]] = relationship(back_populates="user")


class UserBackground(Base):
    __tablename__ = "user_backgrounds"
    __table_args__ = (Index("user_backgrounds_user_id_idx", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="backgrounds")


class Generation(Base):
    __tablename__ = "generations"
    __table_args__ = (Index("generations_user_id_idx", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    job_uid: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    output_key: Mapped[str] = mapped_column(Text, nullable=False)
    output_format: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    dialogue: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    bg_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )

    user: Mapped["User | None"] = relationship(back_populates="generations")
