"""The human gate and the governed release (Lab 12, rule 2, decisions D13 and D14).

Agents draft and flag. A named person approves, edits, overrides or sends back. The only way
anything is published is as the result of an approval by someone whose role allows it: this class
has no public publish method to bypass. Every decision, and every refused attempt, is an audit row
naming the person.

Versions are immutable snapshots. The `current` pointer moves forward on approval and back on a
rollback, and history is never edited. Backed by memory now. The Postgres version keeps the same
methods (CHECKLIST F3).
"""

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

from app.agents.figures import format_with_unit
from app.agents.models import BriefDocument, Option, OptionSet, ValidationReport
from app.core.rbac import Permission, has_permission
from app.domain.enums import BriefStatus
from app.domain.models import AppUser, Frozen
from app.governance.audit import AuditLog

# Checks whose failure means the brief could mislead (a wrong, unsourced or mislabelled figure, or
# a false claim of approval). An escalated draft that fails one of these can never be approved.
# Failures of completeness (V2, V3, V8) can be approved with an acknowledgement. Decision D13.
INTEGRITY_CHECKS = frozenset({"V1", "V4", "V5", "V6", "V7", "V9"})

EditableField = Literal["title", "description", "assumptions", "risks", "trade_offs"]
_LIST_FIELDS = ("assumptions", "risks", "trade_offs")


class GovernanceError(Exception):
    def __init__(self, message: str, report: ValidationReport | None = None) -> None:
        super().__init__(message)
        self.report = report


class PermissionDenied(GovernanceError):
    pass


class EditRejected(GovernanceError):
    """An edit that would break a validation check. The report says which, so it can be fixed."""


class EditRequest(Frozen):
    option_id: str
    field: EditableField
    value: str | list[str]


class Decision(Frozen):
    kind: Literal["approve", "edit", "override", "send_back"]
    reason: str | None = None
    edits: tuple[EditRequest, ...] = ()
    ack_escalation: bool = False


class Edit(Frozen):
    option_id: str
    field: str
    before: str | list[str]
    after: str | list[str]
    by: str
    at: datetime


class Approval(Frozen):
    actor_id: str
    actor_name: str
    role: str
    at: datetime
    ack_escalation: bool


class BriefRecord(Frozen):
    id: str
    run_id: str
    status: BriefStatus
    document: BriefDocument
    validation: ValidationReport
    attempts: int
    escalated: bool
    diagnosis: str | None
    repair_log: tuple[str, ...]
    created_at: datetime
    created_by: str
    history: tuple[ValidationReport, ...] = ()
    approval: Approval | None = None
    edits: tuple[Edit, ...] = ()
    version: int | None = None
    decision_reason: str | None = None


class BriefVersion(Frozen):
    version: int
    brief_id: str
    run_id: str
    document: BriefDocument
    approved_by: str
    approved_by_id: str
    approved_at: datetime
    edits: tuple[Edit, ...]
    escalation_acknowledged: bool


class Change(Frozen):
    section: Literal["figures", "options", "assumptions"]
    kind: Literal["added", "removed", "changed"]
    kpi_key: str | None = None
    option_id: str | None = None
    field: str | None = None
    before: str | None = None
    after: str | None = None


class ApprovalState(Frozen):
    can_approve: bool
    blocked_reason: str | None = None
    needs_acknowledgement: bool = False  # escalated, but only on completeness checks
    failing_checks: list[str] = []


class DecisionResult(Frozen):
    brief: BriefRecord
    version: BriefVersion | None = None


def _as_list(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    return [line for line in value]


def apply_edits(
    doc: BriefDocument, edits: tuple[EditRequest, ...], by: str, at: datetime
) -> tuple[BriefDocument, tuple[Edit, ...]]:
    """Apply a person's edits to option text. Returns the new brief and what changed."""
    options = {o.id: o for s in doc.option_sets for o in s.options}
    recorded: list[Edit] = []
    updated = dict(options)
    for request in edits:
        option = updated.get(request.option_id)
        if option is None:
            raise GovernanceError(f"there is no option {request.option_id}")
        if request.field in _LIST_FIELDS:
            before: str | list[str] = list(getattr(option, request.field))
            after: str | list[str] = _as_list(request.value)
            new_value: Any = tuple(after)
        else:
            if not isinstance(request.value, str):
                raise GovernanceError(f"{request.field} must be text")
            before, after, new_value = getattr(option, request.field), request.value, request.value
        if before == after:
            continue
        updated[request.option_id] = option.model_copy(update={request.field: new_value})
        recorded.append(
            Edit(
                option_id=request.option_id,
                field=request.field,
                before=before,
                after=after,
                by=by,
                at=at,
            )
        )

    new_sets = tuple(
        OptionSet(
            kpi_key=s.kpi_key,
            attempt=s.attempt,
            options=tuple(updated[o.id] for o in s.options),
        )
        for s in doc.option_sets
    )
    return doc.model_copy(update={"option_sets": new_sets}), tuple(recorded)


class GovernanceService:
    def __init__(
        self,
        audit: AuditLog,
        validator: Callable[[BriefDocument], ValidationReport],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        store: Any = None,
    ) -> None:
        """With a `store` (app/db/work_store.py) briefs, versions and the pointer are restored
        from it and every change is written through (decision D31)."""
        self._audit = audit
        self._validate = validator
        self._clock = clock
        self._store = store
        self._briefs: dict[str, BriefRecord] = {}
        self._versions: list[BriefVersion] = []
        self._pointer: int | None = None
        self._rolled_back: set[int] = set()
        self._lock = threading.RLock()
        if store is not None:
            briefs, self._versions, self._pointer, self._rolled_back = store.load()
            self._briefs = {b.id: b for b in briefs}

    def _put(self, record: BriefRecord) -> None:
        self._briefs[record.id] = record
        if self._store is not None:
            self._store.save_brief(record)

    def _pointer_moved(self, by: str) -> None:
        if self._store is not None:
            self._store.save_pointer(self._pointer, set(self._rolled_back), by)

    # --- drafts -----------------------------------------------------------------------------
    def create_draft(
        self,
        *,
        run_id: str,
        document: BriefDocument,
        validation: ValidationReport,
        attempts: int,
        escalated: bool,
        diagnosis: str | None,
        repair_log: tuple[str, ...],
        created_by: str,
        history: tuple[ValidationReport, ...] = (),
    ) -> BriefRecord:
        with self._lock:
            record = BriefRecord(
                id=f"brief-{len(self._briefs) + 1}",
                run_id=run_id,
                status=BriefStatus.ESCALATED if escalated else BriefStatus.DRAFT,
                document=document,
                validation=validation,
                attempts=attempts,
                escalated=escalated,
                diagnosis=diagnosis,
                repair_log=repair_log,
                created_at=self._clock(),
                created_by=created_by,
                history=history,
            )
            self._put(record)
        self._audit.append(
            actor_type="system",
            actor_id="governance",
            action="brief.draft",
            run_id=run_id,
            inputs={"brief_id": record.id},
            outputs={
                "status": record.status.value,
                "attempts": attempts,
                "passed": validation.passed,
            },
        )
        return record

    def get(self, brief_id: str) -> BriefRecord:
        try:
            return self._briefs[brief_id]
        except KeyError:
            raise GovernanceError(f"there is no brief {brief_id!r}") from None

    def briefs(self, status: BriefStatus | None = None) -> list[BriefRecord]:
        with self._lock:
            records = list(self._briefs.values())
        return [r for r in records if status is None or r.status is status]

    # --- the gate ---------------------------------------------------------------------------
    def decide(self, brief_id: str, actor: AppUser, decision: Decision) -> DecisionResult:
        with self._lock:
            brief = self.get(brief_id)
            self._require(actor, Permission.APPROVE, brief, decision.kind)
            if brief.status not in (BriefStatus.DRAFT, BriefStatus.ESCALATED):
                raise GovernanceError(f"this brief has already been {brief.status.value}")

            if decision.kind in ("override", "send_back"):
                return self._close(brief, actor, decision)
            return self._approve(brief, actor, decision)

    def approval_state(self, brief_id: str) -> ApprovalState:
        """Whether this brief can be approved, and if not why. The UI shows this, it never guesses."""
        brief = self.get(brief_id)
        if brief.status not in (BriefStatus.DRAFT, BriefStatus.ESCALATED):
            return ApprovalState(
                can_approve=False,
                blocked_reason=f"This brief has already been {brief.status.value}.",
            )
        report = brief.validation
        if report.passed:
            return ApprovalState(can_approve=True)
        failing = sorted(c.id for c in report.failing)
        if brief.status is not BriefStatus.ESCALATED:
            return ApprovalState(
                can_approve=False,
                blocked_reason="Validation has not passed.",
                failing_checks=failing,
            )
        integrity = sorted(set(failing) & INTEGRITY_CHECKS)
        if integrity:
            return ApprovalState(
                can_approve=False,
                blocked_reason=f"Integrity checks failed ({', '.join(integrity)}). Send it back or override it.",
                failing_checks=failing,
            )
        return ApprovalState(can_approve=True, needs_acknowledgement=True, failing_checks=failing)

    def _require(
        self, actor: AppUser, permission: Permission, brief: BriefRecord | None, action: str
    ) -> None:
        if has_permission(actor, permission):
            return
        self._audit.append(
            actor_type="user",
            actor_id=actor.email,
            action="brief.refused",
            run_id=brief.run_id if brief else None,
            inputs={"brief_id": brief.id if brief else None, "attempted": action},
            outputs={"reason": "the role does not allow it"},
        )
        raise PermissionDenied("your role does not allow you to do that")

    def _close(self, brief: BriefRecord, actor: AppUser, decision: Decision) -> DecisionResult:
        reason = (decision.reason or "").strip()
        if not reason:
            raise GovernanceError("a reason is required")
        status = BriefStatus.OVERRIDDEN if decision.kind == "override" else BriefStatus.RETURNED
        closed = brief.model_copy(update={"status": status, "decision_reason": reason})
        self._put(closed)
        self._audit.append(
            actor_type="user",
            actor_id=actor.email,
            action=f"brief.{decision.kind}",
            run_id=brief.run_id,
            inputs={"brief_id": brief.id, "by": actor.name, "role": actor.role.value},
            outputs={"reason": reason, "status": status.value},
        )
        return DecisionResult(brief=closed)

    def _approve(self, brief: BriefRecord, actor: AppUser, decision: Decision) -> DecisionResult:
        document, report, edits = brief.document, brief.validation, ()
        now = self._clock()

        if decision.kind == "edit":
            if not decision.edits:
                raise GovernanceError("an edit needs at least one change")
            document, edits = apply_edits(brief.document, decision.edits, actor.name, now)
            if not edits:
                raise GovernanceError("an edit needs at least one change")
            report = self._validate(document)
            if not report.passed:
                self._audit.append(
                    actor_type="user",
                    actor_id=actor.email,
                    action="brief.refused",
                    run_id=brief.run_id,
                    inputs={"brief_id": brief.id, "attempted": "edit"},
                    outputs={"failed_checks": [c.id for c in report.failing]},
                )
                raise EditRejected("the edit failed validation, so nothing was published", report)

        # a passing report (possibly the fresh one after an edit) is the normal path
        if not report.passed:
            if brief.status is not BriefStatus.ESCALATED:
                raise GovernanceError(
                    "validation has not passed, so this cannot be approved", report
                )
            failing = {c.id for c in report.failing}
            integrity = sorted(failing & INTEGRITY_CHECKS)
            if integrity:
                raise GovernanceError(
                    f"integrity checks failed ({', '.join(integrity)}), so this cannot be approved. "
                    "Send it back or override it",
                    report,
                )
            if not decision.ack_escalation:
                raise GovernanceError(
                    f"this draft is escalated: acknowledge that checks {', '.join(sorted(failing))} "
                    "did not pass before approving",
                    report,
                )

        acknowledged = brief.escalated and not report.passed and decision.ack_escalation
        version = BriefVersion(
            version=len(self._versions) + 1,
            brief_id=brief.id,
            run_id=brief.run_id,
            document=document,
            approved_by=actor.name,
            approved_by_id=actor.email,
            approved_at=now,
            edits=brief.edits + edits,
            escalation_acknowledged=acknowledged,
        )
        approval = Approval(
            actor_id=actor.email,
            actor_name=actor.name,
            role=actor.role.value,
            at=now,
            ack_escalation=acknowledged,
        )
        published = brief.model_copy(
            update={
                "status": BriefStatus.PUBLISHED,
                "document": document,
                "validation": report,
                "approval": approval,
                "edits": version.edits,
                "version": version.version,
            }
        )
        self._put(published)
        self._release(version)
        self._audit.append(
            actor_type="user",
            actor_id=actor.email,
            action="brief.edit" if edits else "brief.approve",
            run_id=brief.run_id,
            inputs={"brief_id": brief.id, "by": actor.name, "role": actor.role.value},
            outputs={
                "edits": [{"option": e.option_id, "field": e.field} for e in edits],
                "escalation_acknowledged": acknowledged,
                "version": version.version,
            },
        )
        return DecisionResult(brief=published, version=version)

    def _release(self, version: BriefVersion) -> None:
        """Private on purpose. Only an approval in _approve can reach it."""
        self._versions.append(version)
        self._pointer = version.version
        if self._store is not None:
            self._store.save_version(version)
        self._pointer_moved(version.approved_by_id)
        self._audit.append(
            actor_type="system",
            actor_id="governance",
            action="report.publish",
            run_id=version.run_id,
            inputs={"brief_id": version.brief_id},
            outputs={"version": version.version, "approved_by": version.approved_by},
        )

    # --- versions ---------------------------------------------------------------------------
    def current(self) -> BriefVersion | None:
        with self._lock:
            return self._versions[self._pointer - 1] if self._pointer else None

    def versions(self) -> list[BriefVersion]:
        with self._lock:
            return list(self._versions)

    def version(self, number: int) -> BriefVersion:
        with self._lock:
            if not 1 <= number <= len(self._versions):
                raise GovernanceError(f"there is no version {number}")
            return self._versions[number - 1]

    def state_of(self, number: int) -> Literal["current", "rolled_back", "previous"]:
        with self._lock:
            if number == self._pointer:
                return "current"
            return "rolled_back" if number in self._rolled_back else "previous"

    def rollback(self, actor: AppUser, to_version: int, reason: str) -> BriefVersion:
        with self._lock:
            self._require(actor, Permission.ROLLBACK, None, "rollback")
            if not reason.strip():
                raise GovernanceError("a reason is required")
            target = self.version(to_version)
            if to_version == self._pointer:
                raise GovernanceError("that version is already the current one")

            # every version newer than the target that was live is taken out of service
            replaced = [v.version for v in self._versions if v.version > to_version]
            for number in replaced:
                self._rolled_back.add(number)
                brief = self._briefs[self._versions[number - 1].brief_id]
                self._put(brief.model_copy(update={"status": BriefStatus.ROLLED_BACK}))
            self._rolled_back.discard(to_version)
            previous = self._pointer
            self._pointer = to_version
            self._pointer_moved(actor.email)
            self._audit.append(
                actor_type="user",
                actor_id=actor.email,
                action="report.rollback",
                run_id=target.run_id,
                inputs={"by": actor.name, "role": actor.role.value, "from_version": previous},
                outputs={
                    "to_version": to_version,
                    "reason": reason.strip(),
                    "rolled_back": replaced,
                },
            )
            return target

    # --- diff -------------------------------------------------------------------------------
    def diff(self, a: int, b: int) -> list[Change]:
        return diff_documents(self.version(a).document, self.version(b).document)


def _figure_text(f) -> str:
    return f"{format_with_unit(f.value, f.precision, f.unit)} ({f.status.value.replace('_', ' ')})"


def diff_documents(before: BriefDocument, after: BriefDocument) -> list[Change]:
    changes: list[Change] = []

    old_figures, new_figures = {f.key: f for f in before.kpis}, {f.key: f for f in after.kpis}
    for key in sorted(old_figures.keys() | new_figures.keys()):
        old, new = old_figures.get(key), new_figures.get(key)
        if old is None or new is None:
            changes.append(
                Change(
                    section="figures",
                    kind="added" if old is None else "removed",
                    kpi_key=key,
                    after=_figure_text(new) if new else None,
                    before=_figure_text(old) if old else None,
                )
            )
        elif (old.value, old.status, old.target) != (new.value, new.status, new.target):
            changes.append(
                Change(
                    section="figures",
                    kind="changed",
                    kpi_key=key,
                    before=_figure_text(old),
                    after=_figure_text(new),
                )
            )

    def options(doc: BriefDocument) -> dict[str, tuple[str, Option]]:
        return {o.id: (s.kpi_key, o) for s in doc.option_sets for o in s.options}

    old_options, new_options = options(before), options(after)
    for option_id in sorted(old_options.keys() | new_options.keys()):
        old, new = old_options.get(option_id), new_options.get(option_id)
        if old is None or new is None:
            kpi, option = new or old  # type: ignore[misc]
            changes.append(
                Change(
                    section="options",
                    kind="added" if old is None else "removed",
                    kpi_key=kpi,
                    option_id=option_id,
                    after=option.title if new else None,
                    before=option.title if old else None,
                )
            )
            continue
        for field in ("title", "description", "assumptions", "risks", "trade_offs"):
            was, now = getattr(old[1], field), getattr(new[1], field)
            if was != now:
                join = " | ".join if field in _LIST_FIELDS else str
                changes.append(
                    Change(
                        section="options",
                        kind="changed",
                        kpi_key=new[0],
                        option_id=option_id,
                        field=field,
                        before=join(was) if field in _LIST_FIELDS else was,
                        after=join(now) if field in _LIST_FIELDS else now,
                    )
                )

    old_notes = {(a.kind, a.dept_code, a.text) for a in before.assumptions}
    new_notes = {(a.kind, a.dept_code, a.text) for a in after.assumptions}
    for note in sorted(old_notes - new_notes, key=str):
        changes.append(Change(section="assumptions", kind="removed", before=note[2]))
    for note in sorted(new_notes - old_notes, key=str):
        changes.append(Change(section="assumptions", kind="added", after=note[2]))
    return changes
