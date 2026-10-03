from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api import schemas as s
from app.api.deps import AppState, CurrentUser, State, scope_of
from app.core.rbac import PERMISSIONS
from app.core.security import SESSION_COOKIE, issue_token, read_token
from app.domain.models import AppUser

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: AppUser) -> s.UserOut:
    return s.UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        dept_code=user.dept_code,
        school=user.school,
    )


def me_out(user: AppUser, state: AppState) -> s.MeOut:
    scope = scope_of(user, state)
    return s.MeOut(
        user=_user_out(user),
        permissions=sorted(PERMISSIONS[user.role]),
        scope=s.ScopeOut(everything=scope.everything, departments=sorted(scope.departments)),
    )


def _start_session(response: Response, user: AppUser, state: AppState) -> None:
    hours = state.settings.session_hours
    response.set_cookie(
        SESSION_COOKIE,
        issue_token(user.id, state.jwt_secret, hours, version=state.users.session_version(user.id)),
        max_age=hours * 3600,
        httponly=True,  # script on the page can never read the session
        samesite="lax",
        secure=state.settings.cookie_secure,
        path="/",
    )


def _audit(state: AppState, actor_id: str, action: str, outputs: dict | None = None) -> None:
    # never the password, only who tried and what happened
    state.audit.append(
        actor_type="user", actor_id=actor_id, action=action, inputs={}, outputs=outputs or {}
    )


@router.post("/login", response_model=s.MeOut)
def login(body: s.LoginIn, response: Response, state: State) -> s.MeOut:
    email = body.email.strip().lower()
    wait = state.throttle.retry_after(email)
    if wait is not None:
        _audit(state, email, "auth.locked", {"retry_after_seconds": wait})
        minutes = max(1, round(wait / 60))
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many failed attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
            headers={"Retry-After": str(wait)},
        )
    user = state.users.authenticate(body.email, body.password)
    if user is None:
        locked = state.throttle.failed(email)
        _audit(state, email, "auth.login_failed", {"locked": locked})
        # one message for an unknown email and a wrong password, so the form cannot be used to
        # discover which emails have accounts
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    state.throttle.succeeded(email)
    _audit(state, user.email, "auth.login", {"role": user.role.value})
    _start_session(response, user, state)
    return me_out(user, state)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, state: State) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    user_id = read_token(token, state.jwt_secret) if token else None
    user = state.users.get(user_id) if user_id is not None else None
    if user is not None:
        _audit(state, user.email, "auth.logout")
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=s.MeOut)
def me(user: CurrentUser, state: State) -> s.MeOut:
    return me_out(user, state)


@router.get("/demo-users", response_model=list[s.DemoUserOut])
def demo_users(state: State) -> list[s.DemoUserOut]:
    if not state.demo_login_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return [
        s.DemoUserOut(
            email=u.email, name=u.name, role=u.role, dept_code=u.dept_code, school=u.school
        )
        for u in state.users.all()
    ]


@router.post("/demo-login", response_model=s.MeOut)
def demo_login(body: s.DemoLoginIn, response: Response, state: State) -> s.MeOut:
    """One-click sign-in for the seeded synthetic users, so a demo can switch roles quickly.

    Exists only when EDSS_DEMO_LOGIN is on AND data mode is synthetic. In real mode it is a 404.
    """
    if not state.demo_login_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    user = state.users.by_email(body.email)
    if user is None or not user.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    _audit(state, user.email, "auth.demo_login", {"role": user.role.value})
    _start_session(response, user, state)
    return me_out(user, state)
