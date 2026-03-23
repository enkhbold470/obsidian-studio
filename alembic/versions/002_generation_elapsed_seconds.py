"""Add generations.elapsed_seconds (server-side render duration).

Revision ID: 002_elapsed
Revises: 001_initial
Create Date: 2026-03-22

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "002_elapsed"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "generations" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("generations")}
    if "elapsed_seconds" in cols:
        return
    op.add_column(
        "generations",
        sa.Column("elapsed_seconds", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "generations" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("generations")}
    if "elapsed_seconds" not in cols:
        return
    op.drop_column("generations", "elapsed_seconds")
