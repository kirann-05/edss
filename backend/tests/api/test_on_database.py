"""When make test-api-db runs this suite, prove it really ran against PostgreSQL."""

import os

import pytest

from app.db.audit_store import DbAuditLog

pytestmark = pytest.mark.skipif(
    os.environ.get("EDSS_API_ON_DATABASE") != "1", reason="only under make test-api-db"
)


def test_the_shared_app_keeps_its_audit_log_runs_and_briefs_in_the_database(app):
    state = app.state.edss
    assert isinstance(state.audit, DbAuditLog)
    assert state.runs._store is not None and state.governance._store is not None
