"""L6c: a backup restores, matches what was backed up, and its audit chain still verifies."""

import secrets
import stat

import pytest
from sqlalchemy import create_engine, text

from app.db.audit_store import DbAuditLog
from app.db.backup import check, drop, dump, restore_into
from app.db.urls import app_url, owner_url

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def backup(migrated, scratch_db, tmp_path_factory):
    engine = create_engine(app_url(database=scratch_db))
    DbAuditLog(engine).append(actor_type="system", actor_id="test", action="test.before_backup")
    engine.dispose()
    return dump(database=scratch_db, folder=tmp_path_factory.mktemp("backups"))


def test_the_backup_is_readable_by_this_user_only(backup):
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600


def test_a_restored_backup_matches_and_its_audit_chain_verifies(backup, scratch_db):
    report = check(backup, compare_with=scratch_db)
    assert report.ok, report
    assert report.rows["audit_log"] >= 1 and report.chain_checked == report.rows["audit_log"]


def test_a_row_changed_in_a_restored_copy_is_found_by_the_chain_check(backup):
    # the owner can switch the trigger off, which is exactly why the chain check exists
    name = f"edss_tamper_{secrets.token_hex(4)}"
    restore_into(backup, name)
    engine = create_engine(owner_url(database=name))
    try:
        with engine.begin() as conn:
            conn.execute(text("alter table audit_log disable trigger audit_log_no_change"))
            conn.execute(text("update audit_log set action = 'rewritten' where id = 1"))
        verdict = DbAuditLog(engine).verify()
    finally:
        engine.dispose()
        drop(name)
    assert not verdict.ok and verdict.broken_at == 1
