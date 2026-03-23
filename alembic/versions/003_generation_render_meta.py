"""Add generations.render_meta (JSON snapshot of render settings + script).

Revision ID: 003_render_meta
Revises: 002_elapsed
Create Date: 2026-03-22

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003_render_meta"
down_revision: Union[str, None] = "002_elapsed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "generations" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("generations")}
    if "render_meta" in cols:
        return
    op.add_column(
        "generations",
        sa.Column("render_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "generations" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("generations")}
    if "render_meta" not in cols:
        return
    op.drop_column("generations", "render_meta")
