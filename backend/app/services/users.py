"""Users and sign-in. In memory for now, behind the same methods the Postgres version will have.

Seed users are synthetic personas on the reserved .test domain. Nothing here is a real person.
"""

import re
import secrets
import threading
from collections.abc import Collection

from pydantic import ValidationError

from app.core.security import hash_password, verify_password
from app.domain.enums import Role
from app.domain.models import AppUser

SEED_USERS: tuple[AppUser, ...] = (
    AppUser(id=1, email="registrar@edss.test", name="Anand Deshpande", role=Role.REGISTRAR),
    AppUser(id=2, email="principal@edss.test", name="Dr. Kavita Rao", role=Role.PRINCIPAL),
    AppUser(
        id=3,
        email="dean.computing@edss.test",
        name="Dr. Suresh Naik",
        role=Role.DEAN,
        school="School of Computer Science and Engineering",
    ),
    AppUser(id=4, email="hod.cse@edss.test", name="Dr. Priya Joshi", role=Role.HOD, dept_code="CSE"),
    AppUser(id=5, email="hod.civil@edss.test", name="Dr. Imran Shaikh", role=Role.HOD, dept_code="CIVIL"),
    AppUser(id=6, email="council@edss.test", name="Governing Council Member", role=Role.VIEWER),
    AppUser(id=7, email="admin@edss.test", name="System Administrator", role=Role.ADMIN),
)  # fmt: skip


MIN_PASSWORD = 12
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EDITABLE = ("name", "role", "dept_code", "school", "active")


class UserError(ValueError):
    """A change to people or roles that the rules do not allow. The message says why."""


class UserStore:
    def __init__(self, users: tuple[AppUser, ...], password: str) -> None:
        self._by_id = {u.id: u for u in users}
        self._by_email = {u.email.lower(): u for u in users}
        shared = hash_password(password, demo=True)  # one synthetic password for every seed user
        self._hashes = {u.id: shared for u in users}
        self._versions: dict[int, int] = {}
        self._lock = threading.Lock()
        # An unknown email still costs one verification, so response time does not reveal
        # which emails exist.
        self._dummy_hash = hash_password(secrets.token_urlsafe(16), demo=True)

    def session_version(self, user_id: int) -> int:
        return self._versions.get(user_id, 0)

    def _end_sessions(self, user_id: int) -> None:
        self._versions[user_id] = self.session_version(user_id) + 1

    @staticmethod
    def _check_password(password: str) -> None:
        if len(password) < MIN_PASSWORD:
            raise UserError(f"a password needs at least {MIN_PASSWORD} characters")

    def create(
        self,
        *,
        email: str,
        name: str,
        role: Role,
        password: str,
        dept_code: str | None = None,
        school: str | None = None,
        departments: Collection[str] = (),
    ) -> AppUser:
        email = email.strip().lower()
        if not _EMAIL.match(email):
            raise UserError("that is not an email address")
        if not name.strip():
            raise UserError("a person needs a name")
        if dept_code is not None and departments and dept_code not in departments:
            raise UserError(f"there is no department {dept_code!r}")
        self._check_password(password)
        with self._lock:
            if email in self._by_email:
                raise UserError("someone already has that email")
            try:
                user = AppUser(
                    id=max(self._by_id, default=0) + 1, email=email, name=name.strip(),
                    role=role, dept_code=dept_code, school=school,
                )  # fmt: skip
            except ValidationError as error:
                raise UserError(error.errors()[0]["msg"].removeprefix("Value error, ")) from None
            self._by_id[user.id] = user
            self._by_email[email] = user
            self._hashes[user.id] = hash_password(password)
        return user

    def update(
        self,
        user_id: int,
        changes: dict,
        *,
        acting: AppUser,
        departments: Collection[str] = (),
    ) -> tuple[AppUser, dict[str, tuple]]:
        """Apply the changes. Returns the person and what changed, as (before, after) pairs."""
        unknown = set(changes) - set(EDITABLE)
        if unknown:
            raise UserError(f"{sorted(unknown)[0]} cannot be changed here")
        with self._lock:
            user = self._by_id.get(user_id)
            if user is None:
                raise UserError("there is no such person")
            if user.id == acting.id and ("role" in changes or changes.get("active") is False):
                raise UserError("you cannot change your own role or switch off your own account")
            new_dept = changes.get("dept_code")
            if new_dept is not None and departments and new_dept not in departments:
                raise UserError(f"there is no department {new_dept!r}")
            if "name" in changes and not str(changes["name"]).strip():
                raise UserError("a person needs a name")
            try:
                updated = user.model_copy(update=changes)
                updated = AppUser.model_validate(updated.model_dump())  # re-run the role rules
            except ValidationError as error:
                raise UserError(error.errors()[0]["msg"].removeprefix("Value error, ")) from None
            admins_left = [
                u for u in self._by_id.values()
                if u.id != user.id and u.role is Role.ADMIN and u.active
            ]  # fmt: skip
            if (
                (user.role is Role.ADMIN and user.active)
                and not (updated.role is Role.ADMIN and updated.active)
                and not admins_left
            ):
                raise UserError("this is the last active administrator, so it must stay one")
            diff = {
                k: (getattr(user, k), getattr(updated, k))
                for k in EDITABLE
                if getattr(user, k) != getattr(updated, k)
            }
            self._by_id[user.id] = updated
            self._by_email[updated.email.lower()] = updated
            if user.active and not updated.active:
                self._end_sessions(user.id)
        return updated, diff

    def set_password(self, user_id: int, password: str) -> AppUser:
        """A new password, set by an administrator. Every session the person had ends."""
        self._check_password(password)
        with self._lock:
            user = self._by_id.get(user_id)
            if user is None:
                raise UserError("there is no such person")
            self._hashes[user.id] = hash_password(password)
            self._end_sessions(user.id)
        return user

    def get(self, user_id: int) -> AppUser | None:
        return self._by_id.get(user_id)

    def by_email(self, email: str) -> AppUser | None:
        return self._by_email.get(email.strip().lower())

    def authenticate(self, email: str, password: str) -> AppUser | None:
        user = self.by_email(email)
        if user is None:
            verify_password(self._dummy_hash, password)
            return None
        if verify_password(self._hashes[user.id], password) and user.active:
            return user
        return None

    def all(self) -> tuple[AppUser, ...]:
        return tuple(self._by_id.values())


def build_seed_users(password: str | None) -> UserStore:
    """With no password configured, a random one is used, so only demo sign-in can open an account."""
    return UserStore(SEED_USERS, password or secrets.token_urlsafe(24))
