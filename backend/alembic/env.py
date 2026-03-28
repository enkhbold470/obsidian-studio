"""Alembic environment — uses DATABASE_URL or sqlalchemy.url from config."""
from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

from backend.db.models import Base
from backend.db.url import sqlalchemy_url_from_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    u = config.get_main_option("sqlalchemy.url")
    if u and u.strip():
        return u.strip()
    d = os.environ.get("DATABASE_URL", "").strip()
    if not d:
        raise RuntimeError(
            "DATABASE_URL is required (or pass sqlalchemy.url when invoking Alembic)."
        )
    return sqlalchemy_url_from_database_url(d)


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
