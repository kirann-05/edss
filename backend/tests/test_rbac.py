import pytest
from pydantic import ValidationError

from app.core.rbac import PERMISSIONS, Permission, department_scope, has_permission
from app.domain.enums import Role
from app.domain.models import AppUser, Department

P = Permission

# docs/SPEC.md section 2, written out so a change to the matrix has to be a visible change here
EXPECTED = {
    Role.REGISTRAR: {
        P.VIEW_DASHBOARD, P.VIEW_DATA_HEALTH, P.START_RUN, P.REVIEW, P.APPROVE, P.ROLLBACK,
        P.VIEW_REPORTS, P.VIEW_AUDIT, P.MANAGE_SCOPE, P.REFRESH_DATA,
    },
    Role.PRINCIPAL: {
        P.VIEW_DASHBOARD, P.VIEW_DATA_HEALTH, P.START_RUN, P.REVIEW, P.APPROVE, P.ROLLBACK,
        P.VIEW_REPORTS, P.VIEW_AUDIT,
    },
    Role.DEAN: {P.VIEW_DASHBOARD, P.VIEW_DATA_HEALTH, P.START_RUN, P.VIEW_REPORTS},
    Role.HOD: {P.VIEW_DASHBOARD, P.VIEW_DATA_HEALTH, P.VIEW_REPORTS},
    Role.VIEWER: {P.VIEW_REPORTS},
    Role.ADMIN: {P.VIEW_DATA_HEALTH, P.MANAGE_USERS, P.REFRESH_DATA},
}  # fmt: skip

DEPARTMENTS = (
    Department(code="CSE", name="CSE", school="Computing"),
    Department(code="AIML", name="AIML", school="Computing"),
    Department(code="ECE", name="ECE", school="Electronics"),
)


def user(role, *, dept=None, school=None, active=True):
    return AppUser(
        id=1, email="u@edss.test", name="U", role=role, dept_code=dept, school=school, active=active
    )


def test_every_role_is_in_the_matrix_and_matches_the_spec():
    assert set(PERMISSIONS) == set(Role)
    for role, expected in EXPECTED.items():
        assert set(PERMISSIONS[role]) == expected, role


def test_only_registrar_and_principal_can_approve_edit_override_or_roll_back():
    approvers = {r for r in Role if has_permission(user_for(r), P.APPROVE)}
    assert approvers == {Role.REGISTRAR, Role.PRINCIPAL}
    rollbackers = {r for r in Role if has_permission(user_for(r), P.ROLLBACK)}
    assert rollbackers == approvers


def test_an_admin_manages_the_system_but_cannot_approve_or_see_leadership_content():
    admin = user(Role.ADMIN)
    assert not has_permission(admin, P.APPROVE)
    assert not has_permission(admin, P.VIEW_DASHBOARD)
    assert not has_permission(admin, P.VIEW_REPORTS)
    assert has_permission(admin, P.MANAGE_USERS)


def test_a_governing_council_viewer_can_only_read_published_reports():
    assert PERMISSIONS[Role.VIEWER] == {P.VIEW_REPORTS}


def test_a_deactivated_user_has_no_permissions_and_no_scope():
    gone = user(Role.REGISTRAR, active=False)
    assert not any(has_permission(gone, p) for p in P)
    assert department_scope(gone, DEPARTMENTS).allows("CSE") is False


def user_for(role):
    return user(
        role,
        dept="CSE" if role is Role.HOD else None,
        school="Computing" if role is Role.DEAN else None,
    )


class TestScope:
    @pytest.mark.parametrize("role", [Role.REGISTRAR, Role.PRINCIPAL, Role.ADMIN])
    def test_institution_roles_see_every_department(self, role):
        scope = department_scope(user_for(role), DEPARTMENTS)
        assert scope.everything
        assert all(scope.allows(d.code) for d in DEPARTMENTS)

    def test_a_dean_sees_only_departments_in_their_school(self):
        scope = department_scope(user(Role.DEAN, school="Computing"), DEPARTMENTS)
        assert not scope.everything
        assert scope.allows("CSE") and scope.allows("AIML")
        assert not scope.allows("ECE")

    def test_a_hod_sees_only_their_own_department(self):
        scope = department_scope(user(Role.HOD, dept="CSE"), DEPARTMENTS)
        assert scope.allows("CSE")
        assert not scope.allows("AIML")  # same school is not enough for a HOD
        assert not scope.allows("ECE")

    def test_a_viewer_sees_no_department_detail(self):
        scope = department_scope(user(Role.VIEWER), DEPARTMENTS)
        assert not any(scope.allows(d.code) for d in DEPARTMENTS)

    def test_an_unknown_department_is_never_allowed(self):
        assert not department_scope(user(Role.HOD, dept="CSE"), DEPARTMENTS).allows("NOPE")


class TestUserShape:
    def test_a_hod_must_have_a_department(self):
        with pytest.raises(ValidationError, match="department"):
            user(Role.HOD)

    def test_a_dean_must_have_a_school(self):
        with pytest.raises(ValidationError, match="school"):
            user(Role.DEAN)
