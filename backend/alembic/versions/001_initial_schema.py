"""Initial schema (users, generations, user_backgrounds).

Revision ID: 001_initial
Revises:
Create Date: 2026-03-22

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    names = set(insp.get_table_names())

    if "users" not in names:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("email", sa.Text(), nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "gallery_public",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email", name="users_email_unique"),
        )

    names = set(inspect(bind).get_table_names())
    if "generations" not in names:
        op.create_table(
            "generations",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("job_uid", sa.Text(), nullable=False),
            sa.Column("output_key", sa.Text(), nullable=False),
            sa.Column("output_format", sa.Text(), nullable=False),
            sa.Column("topic", sa.Text(), nullable=True),
            sa.Column("dialogue", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("bg_source", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("job_uid", name="generations_job_uid_unique"),
        )
        op.create_index(
            "generations_user_id_idx", "generations", ["user_id"], unique=False
        )

    names = set(inspect(bind).get_table_names())
    if "user_backgrounds" not in names:
        op.create_table(
            "user_backgrounds",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("storage_key", sa.Text(), nullable=False),
            sa.Column("original_filename", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("user_backgrounds_user_id_idx", "user_backgrounds", ["user_id"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_backgrounds CASCADE")
    op.execute("DROP TABLE IF EXISTS generations CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
