"""The audit log in PostgreSQL (rule 9, CHECKLIST L5e).

Same methods and the same hash chain as the in-memory log. One writer at a time across every
process: a transaction-level advisory lock is taken before the last hash is read, so two writers
can never chain from the same row. Ids are given in order under that lock, with no gaps, which
the chain check relies on. Reading happens in the database, so the audit page sees every row
whichever process wrote it.

The app connects as a role that may only read and add rows, and a trigger refuses any change or
delete to every role (migration 0004). The hash chain detects tampering; these make it hard.
"""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, select, text

from app.core.canonical import canonical
from app.db import schema as t
from app.governance.audit import (
    GENESIS_HASH,
    ActorType,
    AuditRow,
    VerifyResult,
    compute_hash,
    verify_rows,
)

_WRITER_LOCK = 794_201  # one number every writer agrees on, nothing else uses it


class DbAuditLog:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def append(
        self,
        *,
        actor_type: ActorType,
        actor_id: str,
        action: str,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        run_id: str | None = None,
        ts: datetime | None = None,
    ) -> AuditRow:
        when = ts or datetime.now(UTC)
        body_inputs = json.loads(canonical(inputs or {}))
        body_outputs = json.loads(canonical(outputs or {}))
        with self._engine.begin() as conn:
            conn.execute(text("select pg_advisory_xact_lock(:k)"), {"k": _WRITER_LOCK})
            last = conn.execute(
                select(t.audit_log.c.id, t.audit_log.c.hash)
                .order_by(t.audit_log.c.id.desc())
                .limit(1)
            ).first()
            previous = last.hash if last else GENESIS_HASH
            row = AuditRow(
                id=(last.id if last else 0) + 1,
                ts=when,
                run_id=run_id,
                actor_type=actor_type,
                actor_id=actor_id,
                action=action,
                inputs=body_inputs,
                outputs=body_outputs,
                prev_hash=previous,
                hash=compute_hash(
                    previous, when, run_id, actor_type, actor_id, action, body_inputs, body_outputs
                ),
            )
            conn.execute(t.audit_log.insert().values(**row.__dict__))
        return row

    def rows(
        self,
        *,
        run_id: str | None = None,
        actor_id: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[AuditRow]:
        c = t.audit_log.c
        query = select(t.audit_log).order_by(c.id)
        if run_id is not None:
            query = query.where(c.run_id == run_id)
        if actor_id is not None:
            query = query.where(c.actor_id == actor_id)
        if action is not None:
            query = query.where(c.action == action)
        if since is not None:
            query = query.where(c.ts >= since)
        if until is not None:
            query = query.where(c.ts <= until)
        with self._engine.connect() as conn:
            found = conn.execute(query).all()
        return [
            AuditRow(
                id=r.id, ts=r.ts.astimezone(UTC), run_id=r.run_id, actor_type=r.actor_type,
                actor_id=r.actor_id, action=r.action, inputs=r.inputs, outputs=r.outputs,
                prev_hash=r.prev_hash, hash=r.hash,
            )
            for r in found
        ]  # fmt: skip

    def verify(self) -> VerifyResult:
        return verify_rows(self.rows())

    def actions(self) -> list[str]:
        with self._engine.connect() as conn:
            return list(
                conn.execute(
                    select(t.audit_log.c.action).distinct().order_by(t.audit_log.c.action)
                ).scalars()
            )
