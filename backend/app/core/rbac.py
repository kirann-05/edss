"""Roles, permissions and department scope (docs/SPEC.md section 2).

Two separate questions are answered here and kept apart on purpose:

  has_permission   may this role do this kind of thing at all?
  department_scope which departments' record-level detail may this person see?

A HOD never sees another department's detail, whatever else they may do. Every route checks
both. The UI hides what a person cannot use, but only as a convenience: authorisation lives here.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from app.domain.enums import Role
from app.domain.models import AppUser, Department


class Permission(StrEnum):
    VIEW_DASHBOARD = "view_dashboard"  # institution KPIs and domain metrics
    VIEW_DATA_HEALTH = "view_data_health"
    START_RUN = "start_run"
    REVIEW = "review"  # review queue and draft briefs
    APPROVE = "approve"  # approve, edit or override a draft
    ROLLBACK = "rollback"
    VIEW_REPORTS = "view_reports"  # approved, published reports
    VIEW_AUDIT = "view_audit"
    MANAGE_USERS = "manage_users"
    MANAGE_SCOPE = "manage_scope"  # Registrar authorises a domain's read scope
    REFRESH_DATA = "refresh_data"


P = Permission

_LEADERSHIP = {P.VIEW_DASHBOARD, P.VIEW_DATA_HEALTH, P.START_RUN, P.VIEW_REPORTS}
_APPROVER = _LEADERSHIP | {P.REVIEW, P.APPROVE, P.ROLLBACK, P.VIEW_AUDIT}

PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.REGISTRAR: frozenset(_APPROVER | {P.MANAGE_SCOPE, P.REFRESH_DATA}),
    Role.PRINCIPAL: frozenset(_APPROVER),
    Role.DEAN: frozenset(_LEADERSHIP),
    Role.HOD: frozenset({P.VIEW_DASHBOARD, P.VIEW_DATA_HEALTH, P.VIEW_REPORTS}),
    Role.VIEWER: frozenset({P.VIEW_REPORTS}),
    Role.ADMIN: frozenset({P.VIEW_DATA_HEALTH, P.MANAGE_USERS, P.REFRESH_DATA}),
}


def has_permission(user: AppUser, permission: Permission) -> bool:
    return user.active and permission in PERMISSIONS[user.role]


@dataclass(frozen=True)
class Scope:
    """The departments whose record-level detail a person may see."""

    everything: bool
    departments: frozenset[str] = frozenset()

    def allows(self, dept_code: str) -> bool:
        return self.everything or dept_code in self.departments


NO_SCOPE = Scope(everything=False)


def department_scope(user: AppUser, departments: Iterable[Department]) -> Scope:
    if not user.active:
        return NO_SCOPE
    if user.role in (Role.REGISTRAR, Role.PRINCIPAL, Role.ADMIN):
        return Scope(everything=True)
    if user.role is Role.DEAN:
        return Scope(everything=False, departments=frozenset(
            d.code for d in departments if d.school == user.school
        ))  # fmt: skip
    if user.role is Role.HOD and user.dept_code:
        return Scope(everything=False, departments=frozenset({user.dept_code}))
    return NO_SCOPE
