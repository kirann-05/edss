"""L5e: the audit log in PostgreSQL. One writer at a time, and nobody can rewrite it."""

import threading

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.db.audit_store import DbAuditLog
from app.db.urls import app_url

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def app_engine(migrated, scratch_db):
    engine = create_engine(app_url(database=scratch_db))
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def log(app_engine):
    audit = DbAuditLog(app_engine)
    audit.append(actor_type="system", actor_id="test", action="test.start", inputs={"n": 1})
    return audit


def test_the_app_role_can_add_and_read_and_the_chain_verifies(log):
    row = log.append(
        actor_type="user", actor_id="registrar@edss.test", action="test.read", outputs={"ok": True}
    )
    back = log.rows(action="test.read")[-1]
    assert back == row
    assert log.verify().ok


@pytest.mark.parametrize(
    "statement",
    ["update audit_log set action = 'rewritten'", "delete from audit_log", "truncate audit_log"],
)
def test_the_app_role_cannot_change_delete_or_empty_it(log, app_engine, statement):
    with pytest.raises(DBAPIError, match="permission denied"), app_engine.begin() as conn:
        conn.execute(text(statement))


@pytest.mark.parametrize(
    "statement",
    ["update audit_log set action = 'rewritten'", "delete from audit_log", "truncate audit_log"],
)
def test_not_even_the_owner_can(log, migrated, statement):
    with pytest.raises(DBAPIError, match="append-only"), migrated.begin() as conn:
        conn.execute(text(statement))


def test_two_processes_writing_at_once_still_make_one_unbroken_chain(log, scratch_db):
    # two engines stand for two processes: they share nothing but the database
    writers = [DbAuditLog(create_engine(app_url(database=scratch_db))) for _ in range(2)]
    before = len(log.rows())

    def write(audit, n):
        for i in range(n):
            audit.append(
                actor_type="agent",
                actor_id=f"writer-{id(audit)}",
                action="test.concurrent",
                inputs={"i": i},
            )

    threads = [threading.Thread(target=write, args=(writers[i % 2], 15)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    rows = log.rows()
    assert len(rows) == before + 90
    assert [r.id for r in rows] == list(range(1, len(rows) + 1))  # no gap, no repeat
    assert log.verify().ok


def test_the_app_role_cannot_touch_the_migration_record(app_engine):
    with pytest.raises(DBAPIError, match="permission denied"), app_engine.connect() as conn:
        conn.execute(text("select * from alembic_version"))
