"""The append-only, hash-chained audit log (rule 9, Lab 6, decision D18).

Every step of a run, and every decision a person makes, is a row. Each row carries the hash of
the row before it, so changing, removing or reordering any row breaks every hash after it, and
`verify_rows` says exactly where. Inputs and outputs are logged, not just messages.

Appends take a lock, so parallel nodes cannot race on the previous hash: the chain has a single
writer. The Postgres version does the same with an advisory lock and a database role that can
INSERT and SELECT on the table but never UPDATE or DELETE (CHECKLIST F4).
"""

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

GENESIS_HASH = "0" * 64
ActorType = Literal["user", "agent", "system"]


def _default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")  # text, never a float, so a figure hashes the same everywhere
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (set, frozenset, tuple)):
        return sorted(value, key=str) if isinstance(value, (set, frozenset)) else list(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"cannot audit a value of type {type(value).__name__}")


def canonical(value: Any) -> str:
    """One text form per content, whatever the key order, so the same facts always hash alike."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_default)


def compute_hash(
    prev_hash: str,
    ts: datetime,
    run_id: str | None,
    actor_type: str,
    actor_id: str,
    action: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
) -> str:
    body = canonical(
        {
            "ts": ts,
            "run_id": run_id,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "action": action,
            "inputs": inputs,
            "outputs": outputs,
        }
    )
    return hashlib.sha256((prev_hash + body).encode()).hexdigest()


@dataclass(frozen=True)
class AuditRow:
    id: int
    ts: datetime
    run_id: str | None
    actor_type: str
    actor_id: str
    action: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    prev_hash: str
    hash: str


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    checked: int
    broken_at: int | None = None  # id of the first row that does not chain
    reason: str | None = None


def verify_rows(rows: list[AuditRow]) -> VerifyResult:
    """Recompute the chain from the rows alone. The first row that does not hold is reported."""
    previous_hash = GENESIS_HASH
    previous_id = 0
    for checked, row in enumerate(rows):
        if row.prev_hash != previous_hash:
            return VerifyResult(False, checked, row.id, "does not follow the row before it")
        expected = compute_hash(
            row.prev_hash,
            row.ts,
            row.run_id,
            row.actor_type,
            row.actor_id,
            row.action,
            row.inputs,
            row.outputs,
        )
        if row.hash != expected:
            return VerifyResult(False, checked, row.id, "its content no longer matches its hash")
        if row.id != previous_id + 1:
            return VerifyResult(False, checked, row.id, "a row is missing or out of order")
        previous_hash, previous_id = row.hash, row.id
    return VerifyResult(True, len(rows))


@dataclass
class AuditLog:
    _rows: list[AuditRow] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

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
        # the lock is what makes the chain safe when four domain nodes finish at once
        with self._lock:
            previous = self._rows[-1].hash if self._rows else GENESIS_HASH
            when = ts or datetime.now(UTC)
            body_inputs = json.loads(canonical(inputs or {}))
            body_outputs = json.loads(canonical(outputs or {}))
            row = AuditRow(
                id=len(self._rows) + 1,
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
            self._rows.append(row)
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
        """A copy, filtered. Callers can never reach the log's own list."""
        with self._lock:
            snapshot = list(self._rows)
        return [
            r
            for r in snapshot
            if (run_id is None or r.run_id == run_id)
            and (actor_id is None or r.actor_id == actor_id)
            and (action is None or r.action == action)
            and (since is None or r.ts >= since)
            and (until is None or r.ts <= until)
        ]

    def verify(self) -> VerifyResult:
        return verify_rows(self.rows())
