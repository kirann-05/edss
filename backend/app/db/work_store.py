"""Runs, briefs, versions and the current-report pointer in PostgreSQL (CHECKLIST L5f).

The run service and the governance service keep their rules; these classes load what they hold
and write each change through (decision D31). Every record is also kept whole as JSON beside the
columns a person would query, so it comes back exactly as it went in.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import Engine, select, update
from sqlalchemy.dialects.postgresql import insert

from app.db import schema as t
from app.governance.service import BriefRecord, BriefVersion
from app.services.runs import RunRecord, RunStatus

_RUN = TypeAdapter(RunRecord)
POINTER = "current_report"


def _number(identifier: str) -> int:
    return int(identifier.rsplit("-", 1)[-1])


class RunRows:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(self) -> list[RunRecord]:
        with self._engine.connect() as conn:
            details = conn.execute(select(t.run.c.detail)).scalars().all()
        return sorted((_RUN.validate_python(d) for d in details), key=lambda r: _number(r.id))

    def save(self, record: RunRecord) -> None:
        detail = _RUN.dump_python(record, mode="json")
        values: dict[str, Any] = {
            "id": record.id, "request": record.request,
            "clarifications": detail["answers"], "plan": detail["plan"],
            "plan_locked_at": record.plan.locked_at if record.plan else None,
            "status": record.status.value, "created_by": record.created_by,
            "created_at": record.created_at,
            "finished_at": datetime.now(UTC) if record.status in (RunStatus.COMPLETED, RunStatus.FAILED) else None,
            "detail": detail,
        }  # fmt: skip
        with self._engine.begin() as conn:
            _upsert(conn, t.run, "id", values)


class GovernanceRows:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(self) -> tuple[list[BriefRecord], list[BriefVersion], int | None, set[int]]:
        with self._engine.connect() as conn:
            briefs = [
                BriefRecord.model_validate(d)
                for d in conn.execute(select(t.brief.c.detail)).scalars().all()
            ]
            rows = conn.execute(
                select(t.brief_version.c.detail, t.brief_version.c.rolled_back).order_by(
                    t.brief_version.c.version
                )
            ).all()
            pointer = conn.execute(
                select(t.brief_version.c.version)
                .join(t.system_pointer, t.system_pointer.c.brief_version_id == t.brief_version.c.id)
                .where(t.system_pointer.c.name == POINTER)
            ).scalar_one_or_none()
        versions = [BriefVersion.model_validate(r.detail) for r in rows]
        rolled_back = {v.version for v, r in zip(versions, rows, strict=True) if r.rolled_back}
        return sorted(briefs, key=lambda b: _number(b.id)), versions, pointer, rolled_back

    def save_brief(self, record: BriefRecord) -> None:
        detail = record.model_dump(mode="json")
        values = {
            "id": record.id, "run_id": record.run_id, "status": record.status.value,
            "content": detail["document"], "validation": detail["validation"],
            "created_at": record.created_at, "detail": detail,
        }  # fmt: skip
        with self._engine.begin() as conn:
            _upsert(conn, t.brief, "id", values)

    def save_version(self, version: BriefVersion) -> None:
        detail = version.model_dump(mode="json")
        with self._engine.begin() as conn:
            conn.execute(
                t.brief_version.insert().values(
                    brief_id=version.brief_id, version=version.version, content=detail["document"],
                    approved_by=version.approved_by, approved_at=version.approved_at,
                    edits=detail["edits"], created_at=datetime.now(UTC), detail=detail,
                )
            )  # fmt: skip

    def save_pointer(self, pointer: int | None, rolled_back: set[int], by: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                update(t.brief_version).values(
                    rolled_back=t.brief_version.c.version.in_(rolled_back or {-1})
                )
            )
            version_id = None
            if pointer is not None:
                version_id = conn.execute(
                    select(t.brief_version.c.id).where(t.brief_version.c.version == pointer)
                ).scalar_one()
            _upsert(
                conn, t.system_pointer, "name",
                {"name": POINTER, "brief_version_id": version_id, "updated_by": by, "updated_at": datetime.now(UTC)},
            )  # fmt: skip


def _upsert(conn, table, key: str, values: dict[str, Any]) -> None:
    statement = insert(table).values(**values)
    conn.execute(
        statement.on_conflict_do_update(
            index_elements=[key], set_={k: statement.excluded[k] for k in values if k != key}
        )
    )
