"""Backups of the EDSS database, and a restore that proves a backup is good (CHECKLIST L6c).

Operations tooling, never used by the running app. It runs pg_dump and pg_restore inside the
database container from compose.yaml, so this machine needs no PostgreSQL client. On a server with
PostgreSQL installed directly, docs/RUNBOOK.md gives the same commands without Docker.

A backup is only as good as its restore, so `check` restores into a throwaway database and asks
the questions that matter: does every table hold what the live one holds, and does the audit chain
still verify, row by row, from the first entry.
"""

import os
import secrets
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from sqlalchemy import create_engine, func, select

from app.db import schema as t
from app.db.audit_store import DbAuditLog
from app.db.urls import owner_url

ROOT = Path(__file__).resolve().parents[3]
BACKUPS = ROOT / "backups"  # gitignored: a backup holds the data, and real data never leaves here
COUNTED = ("department", "metric_fact", "research_publication", "app_user", "run", "brief",
           "brief_version", "audit_log", "brief_embedding")  # fmt: skip


def _in_db_container(*args: str, stdin=None, stdout=None) -> subprocess.CompletedProcess:
    command = ["docker", "compose", "--env-file", str(ROOT / ".env"), "exec", "-T", "db", *args]
    return subprocess.run(
        command, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, check=True, cwd=ROOT
    )


def dump(database: str = "edss", folder: Path = BACKUPS) -> Path:
    folder.mkdir(exist_ok=True)
    os.chmod(folder, 0o700)
    path = folder / f"{database}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.dump"
    with open(path, "wb") as out:
        _in_db_container(
            "pg_dump", "-U", "edss_owner", "-d", database, "--format=custom", stdout=out
        )
    os.chmod(path, 0o600)
    return path


def _admin() -> psycopg.Connection:
    url = owner_url(database="postgres")
    return psycopg.connect(
        host=url.host, port=url.port, user=url.username, password=url.password, dbname="postgres",
        autocommit=True,
    )  # fmt: skip


def restore_into(path: Path, database: str) -> None:
    with _admin() as admin:
        admin.execute(f'create database "{database}"')
    with open(path, "rb") as source:
        _in_db_container(
            "pg_restore", "-U", "edss_owner", "-d", database, "--exit-on-error", stdin=source
        )


def drop(database: str) -> None:
    with _admin() as admin:
        admin.execute(f'drop database if exists "{database}" with (force)')


def counts(database: str) -> dict[str, int]:
    engine = create_engine(owner_url(database=database))
    try:
        with engine.connect() as conn:
            return {
                name: conn.execute(
                    select(func.count()).select_from(t.metadata.tables[name])
                ).scalar_one()
                for name in COUNTED
            }
    finally:
        engine.dispose()


@dataclass
class RestoreReport:
    backup: Path
    rows: dict[str, int]
    differences: dict[str, tuple[int, int]]  # table: (live, restored)
    chain_ok: bool
    chain_checked: int
    chain_reason: str | None

    @property
    def ok(self) -> bool:
        return self.chain_ok and not self.differences


def check(path: Path, compare_with: str | None = "edss") -> RestoreReport:
    """Restore into a throwaway database, compare it, verify the audit chain, and drop it."""
    scratch = f"edss_restore_{secrets.token_hex(4)}"
    try:
        restore_into(path, scratch)
        restored = counts(scratch)
        live = counts(compare_with) if compare_with else restored
        engine = create_engine(owner_url(database=scratch))
        try:
            verdict = DbAuditLog(engine).verify()
        finally:
            engine.dispose()
    finally:
        drop(scratch)
    differences = {k: (live[k], restored[k]) for k in COUNTED if live[k] != restored[k]}
    return RestoreReport(path, restored, differences, verdict.ok, verdict.checked, verdict.reason)
