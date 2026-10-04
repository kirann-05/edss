"""A throwaway database per test session, made and dropped by the owner. Never the real `edss`."""

import os
import secrets

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from app.db.urls import owner_url


def _admin():
    url = owner_url(database="postgres")
    return psycopg.connect(
        host=url.host, port=url.port, user=url.username, password=url.password,
        dbname="postgres", autocommit=True, connect_timeout=3,
    )  # fmt: skip


@pytest.fixture(scope="session")
def scratch_db():
    try:
        admin = _admin()
    except (psycopg.OperationalError, RuntimeError) as error:
        if os.environ.get("EDSS_REQUIRE_DB") == "1":
            raise
        pytest.skip(f"PostgreSQL is not running (make db-up): {error}")
    name = f"edss_test_{secrets.token_hex(4)}"
    admin.execute(f'create database "{name}"')
    try:
        yield name
    finally:
        admin.execute(f'drop database "{name}" with (force)')
        admin.close()


ALEMBIC_INI = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")


@pytest.fixture(scope="session")
def migrated(scratch_db, monkeypatch_module):
    monkeypatch_module.setenv("EDSS_DB_NAME", scratch_db)
    command.upgrade(Config(ALEMBIC_INI), "head")
    engine = create_engine(owner_url(database=scratch_db))
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def monkeypatch_module():
    with pytest.MonkeyPatch.context() as patch:
        yield patch
