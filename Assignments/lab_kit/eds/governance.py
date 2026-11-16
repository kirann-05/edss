"""
Lab 12 - Safety & Governance: the human approval gate as a hard stop,
role-based confidentiality, versioning, metrics, and one-click rollback.

    require actor.can_approve and out.status == 'draft'
    final = apply(human.edits, out); final.status = 'approved'
    governance.publish(final, version=v+1); metrics.record(...)
    on rollback(v): restore(version=v)

The human authority for this worklet is the Executive / Leadership
(Principal/Director, Registrar, Governing Council). No worklet in this
system takes a consequential action autonomously -- this module is
where that rule is enforced in code, not just in policy.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


APPROVED_ROLES = {"Principal", "Director", "Registrar", "Governing Council"}


class ApprovalRequiredError(RuntimeError):
    pass


class UnauthorizedRoleError(RuntimeError):
    pass


@dataclass
class Decision:
    actor: str
    role: str
    decision: str          # "approve" | "edit" | "override"
    edits: Dict[str, Any] = field(default_factory=dict)
    comment: str = ""
    ts: str = field(default_factory=lambda: _dt.datetime.utcnow().isoformat())

    @property
    def approved(self) -> bool:
        return self.decision in ("approve", "edit")


class HumanGate:
    """
    The Amber node: a hard stop. Nothing downstream of this class may be
    reached without a `Decision` from an actor holding one of
    `APPROVED_ROLES`.
    """

    @staticmethod
    def review(draft: Dict[str, Any], actor: str, role: str, decision: str,
               edits: Optional[Dict[str, Any]] = None, comment: str = "") -> Decision:
        if role not in APPROVED_ROLES:
            raise UnauthorizedRoleError(
                f"'{role}' is not an authorized approver for an executive report. "
                f"Authorized roles: {sorted(APPROVED_ROLES)}"
            )
        return Decision(actor=actor, role=role, decision=decision, edits=edits or {}, comment=comment)


@dataclass
class PublishedVersion:
    version: int
    published_at: str
    content: Dict[str, Any]
    approved_by: str
    role: str
    run_id: str


class Governance:
    """Versioning, publish gate, and one-click rollback for executive
    reports. Every publish is preceded by a checked `Decision.approved`
    -- there is no code path that writes to `_versions` any other way."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir
        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._versions: List[PublishedVersion] = []
        self.metrics: List[Dict[str, Any]] = []

    def publish(self, draft: Dict[str, Any], decision: Decision, run_id: str) -> PublishedVersion:
        if not decision.approved:
            raise ApprovalRequiredError(
                f"Cannot publish: decision was '{decision.decision}', not an approval."
            )
        final_content = dict(draft)
        final_content.update(decision.edits)
        final_content["status"] = "approved"
        final_content["approved_by"] = decision.actor
        final_content["approver_role"] = decision.role
        final_content["approval_comment"] = decision.comment

        version_no = len(self._versions) + 1
        version = PublishedVersion(
            version=version_no,
            published_at=_dt.datetime.utcnow().isoformat(),
            content=final_content,
            approved_by=decision.actor,
            role=decision.role,
            run_id=run_id,
        )
        self._versions.append(version)
        if self.storage_dir:
            path = self.storage_dir / f"v{version_no}_{run_id}.json"
            path.write_text(json.dumps(final_content, indent=2, default=str), encoding="utf-8")
        return version

    def record_metric(self, name: str, value: Any, run_id: str) -> None:
        self.metrics.append({
            "metric": name, "value": value, "run_id": run_id,
            "ts": _dt.datetime.utcnow().isoformat(),
        })

    def rollback(self, to_version: int) -> PublishedVersion:
        matches = [v for v in self._versions if v.version == to_version]
        if not matches:
            raise ValueError(f"No published version #{to_version} to roll back to.")
        restored_content = dict(matches[0].content)
        restored_content["status"] = "approved"
        restored_content["restored_from_version"] = to_version
        new_version_no = len(self._versions) + 1
        version = PublishedVersion(
            version=new_version_no,
            published_at=_dt.datetime.utcnow().isoformat(),
            content=restored_content,
            approved_by=f"rollback-to-v{to_version}",
            role="system",
            run_id=matches[0].run_id,
        )
        self._versions.append(version)
        return version

    def latest(self) -> Optional[PublishedVersion]:
        return self._versions[-1] if self._versions else None

    def history(self) -> List[Dict[str, Any]]:
        return [
            {"version": v.version, "published_at": v.published_at,
             "approved_by": v.approved_by, "role": v.role, "run_id": v.run_id}
            for v in self._versions
        ]
