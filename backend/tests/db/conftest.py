"""A throwaway database per test session, made and dropped by the owner. Never the real `edss`."""

import os
import secrets

import psycopg
import pytest

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
