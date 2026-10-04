"""Alembic's entry point. Migrations run as the database owner, from .env (app/db/urls.py)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.db.schema import metadata, ours
from app.db.urls import owner_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def run_migrations_offline() -> None:
    """Write the SQL without connecting, for a person to read: alembic upgrade head --sql."""
    context.configure(
        url=owner_url().render_as_string(hide_password=True),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(owner_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_object=ours
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
