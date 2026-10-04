"""An app role that cannot rewrite the audit log, and a trigger that stops anyone else.

Written by hand. The app connects as edss_app (CHECKLIST L5e): it may read and add to the audit
log but never change, delete or empty it. The trigger refuses those to every role, the owner too,
so rewriting history needs a deliberate migration, not a mistake. The role's password is set
outside migrations, by scripts/db_roles.py, so no password is ever written in a migration.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'edss_app') THEN "
        "CREATE ROLE edss_app NOLOGIN; END IF; END $$"
    )
    op.execute("GRANT USAGE ON SCHEMA public TO edss_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO edss_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO edss_app")
    op.execute("REVOKE ALL ON alembic_version FROM edss_app")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM edss_app")
    # tables a later migration adds get the same grants, and the audit log stays as it is here
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO edss_app"
    )
    op.execute(
        "CREATE FUNCTION audit_log_append_only() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION 'the audit log is append-only: % is refused', TG_OP; END $$"
    )
    op.execute(
        "CREATE TRIGGER audit_log_no_change BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_log_append_only()"
    )
    op.execute(
        "CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit_log_append_only()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER audit_log_no_truncate ON audit_log")
    op.execute("DROP TRIGGER audit_log_no_change ON audit_log")
    op.execute("DROP FUNCTION audit_log_append_only()")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM edss_app"
    )
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM edss_app")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM edss_app")
    op.execute("REVOKE USAGE ON SCHEMA public FROM edss_app")
    # the role itself is shared by every database on the server, so it is left in place
