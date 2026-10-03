"""Shared request dependencies: who is signed in, what they may do, and what they may see."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status

from app.core.config import Settings
from app.core.rbac import Permission, Scope, department_scope, has_permission
from app.core.security import SESSION_COOKIE, read_token
from app.domain.models import AppUser
from app.services.store import DataStore, UnknownPeriodError
from app.services.users import UserStore


@dataclass
class AppState:
    settings: Settings
    store: DataStore
    users: UserStore
    jwt_secret: str

    @property
    def demo_login_enabled(self) -> bool:
        # The flag alone is not enough: demo sign-in never exists outside synthetic data mode
        return self.settings.edss_demo_login and self.settings.data_mode == "synthetic"


def get_state(request: Request) -> AppState:
    return request.app.state.edss


State = Annotated[AppState, Depends(get_state)]


def current_user(request: Request, state: State) -> AppUser:
    token = request.cookies.get(SESSION_COOKIE)
    user_id = read_token(token, state.jwt_secret) if token else None
    user = state.users.get(user_id) if user_id is not None else None
    if user is None or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


CurrentUser = Annotated[AppUser, Depends(current_user)]


def require(permission: Permission):
    """A dependency that signs the person in (401) and then checks the permission (403)."""

    def dependency(user: CurrentUser) -> AppUser:
        if not has_permission(user, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to do that")
        return user

    return dependency


def scope_of(user: AppUser, state: AppState) -> Scope:
    return department_scope(user, state.store.dataset.departments)


def resolve_period(state: State, period: Annotated[str | None, Query()] = None) -> str:
    try:
        return state.store.resolve_period(period)
    except UnknownPeriodError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown period {period!r}") from None


Period = Annotated[str, Depends(resolve_period)]
