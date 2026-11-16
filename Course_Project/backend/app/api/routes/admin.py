"""Admin: people and roles (the Administrator) and data access (the Registrar, FR-2).

The two are kept apart on purpose. An Administrator manages accounts but can never approve or
read content they are not given, and the Registrar authorises which areas may be read without
managing accounts. Every change is audited, a password never is.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.skills.plan_skill import AREAS
from app.api import schemas as s
from app.api.deps import AppState, CurrentUser, State, require
from app.core.rbac import Permission, has_permission
from app.domain.enums import Domain, Role
from app.domain.models import AppUser
from app.services.users import MIN_PASSWORD, UserError

router = APIRouter(prefix="/admin", tags=["admin"])
UserAdmin = Depends(require(Permission.MANAGE_USERS))
ScopeAdmin = Depends(require(Permission.MANAGE_SCOPE))


def _user_out(user: AppUser) -> s.AdminUserOut:
    return s.AdminUserOut(
        id=user.id, email=user.email, name=user.name, role=user.role,
        dept_code=user.dept_code, school=user.school, active=user.active,
    )  # fmt: skip


def _departments(state: AppState) -> set[str]:
    return {d.code for d in state.store.dataset.departments}


def _refuse(error: UserError) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


def _audit(state: AppState, actor: AppUser, action: str, inputs: dict, outputs: dict) -> None:
    state.audit.append(
        actor_type="user", actor_id=actor.email, action=action,
        inputs={"by": actor.name, "role": actor.role.value, **inputs}, outputs=outputs,
    )  # fmt: skip


@router.get("/options", response_model=s.AdminOptionsOut)
def options(state: State, user: CurrentUser) -> s.AdminOptionsOut:
    if not (
        has_permission(user, Permission.MANAGE_USERS)
        or has_permission(user, Permission.MANAGE_SCOPE)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to do that")
    departments = state.store.dataset.departments
    return s.AdminOptionsOut(
        roles=list(Role),
        departments=[
            s.DepartmentOptionOut(code=d.code, name=d.name, school=d.school) for d in departments
        ],
        schools=sorted({d.school for d in departments}),
        min_password=MIN_PASSWORD,
        areas=list(AREAS),
    )


# --- people and roles -------------------------------------------------------------------------
@router.get("/users", response_model=list[s.AdminUserOut])
def users(state: State, user: AppUser = UserAdmin) -> list[s.AdminUserOut]:
    return [_user_out(u) for u in sorted(state.users.all(), key=lambda u: (u.role.value, u.name))]


@router.post("/users", response_model=s.AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: s.CreateUserIn, state: State, user: AppUser = UserAdmin) -> s.AdminUserOut:
    try:
        created = state.users.create(
            email=body.email, name=body.name, role=body.role, password=body.password,
            dept_code=body.dept_code, school=body.school, departments=_departments(state),
        )  # fmt: skip
    except UserError as error:
        raise _refuse(error) from None
    _audit(
        state, user, "user.create", {"email": created.email},
        {"id": created.id, "role": created.role.value, "dept_code": created.dept_code, "school": created.school},
    )  # fmt: skip
    return _user_out(created)


@router.patch("/users/{user_id}", response_model=s.AdminUserOut)
def update_user(
    user_id: int, body: s.UpdateUserIn, state: State, user: AppUser = UserAdmin
) -> s.AdminUserOut:
    changes = body.model_dump(exclude_unset=True)
    try:
        updated, diff = state.users.update(
            user_id, changes, acting=user, departments=_departments(state)
        )
    except UserError as error:
        raise _refuse(error) from None
    _audit(
        state, user, "user.update", {"user_id": user_id, "email": updated.email},
        {"changes": {k: [str(b) if b is not None else None, str(a) if a is not None else None]
                     for k, (b, a) in diff.items()}},
    )  # fmt: skip
    return _user_out(updated)


@router.post("/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: int, body: s.PasswordIn, state: State, user: AppUser = UserAdmin
) -> None:
    try:
        target = state.users.set_password(user_id, body.password)
    except UserError as error:
        raise _refuse(error) from None
    _audit(
        state,
        user,
        "user.password_reset",
        {"user_id": user_id, "email": target.email},
        {"sessions_ended": True},
    )


# --- data access --------------------------------------------------------------------------------
def _grant_out(state: AppState, grant) -> s.ScopeGrantOut:
    return s.ScopeGrantOut(
        domain=grant.domain, dept_code=grant.dept_code, granted_by=grant.granted_by,
        granted_on=grant.granted_on, expires_on=grant.expires_on, active=grant.active,
        state=state.scopes.state_of(grant, state.store.today),  # type: ignore[arg-type]
    )  # fmt: skip


@router.get("/scope-grants", response_model=list[s.ScopeGrantOut])
def scope_grants(state: State, user: AppUser = ScopeAdmin) -> list[s.ScopeGrantOut]:
    return [_grant_out(state, g) for g in sorted(state.scopes.all(), key=lambda g: g.domain.value)]


@router.post("/scope-grants", response_model=s.ScopeGrantOut)
def grant(body: s.GrantIn, state: State, user: AppUser = ScopeAdmin) -> s.ScopeGrantOut:
    today = state.store.today
    if body.domain not in AREAS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Access is granted to one of the four areas"
        )
    if body.expires_on is not None and body.expires_on <= today:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The expiry must be after today")
    granted = state.scopes.grant(body.domain, user.email, today, body.expires_on)
    _audit(
        state,
        user,
        "scope.grant",
        {"domain": body.domain.value},
        {"expires_on": str(granted.expires_on)},
    )
    return _grant_out(state, granted)


@router.post("/scope-grants/{domain}/revoke", response_model=list[s.ScopeGrantOut])
def revoke(domain: Domain, state: State, user: AppUser = ScopeAdmin) -> list[s.ScopeGrantOut]:
    if domain not in AREAS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown area")
    state.scopes.revoke(domain)
    _audit(state, user, "scope.revoke", {"domain": domain.value}, {})
    return scope_grants(state, user)
