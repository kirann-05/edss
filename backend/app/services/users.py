"""Users and sign-in. In memory for now, behind the same methods the Postgres version will have.

Seed users are synthetic personas on the reserved .test domain. Nothing here is a real person.
"""

import secrets

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


class UserStore:
    def __init__(self, users: tuple[AppUser, ...], password: str) -> None:
        self._by_id = {u.id: u for u in users}
        self._by_email = {u.email.lower(): u for u in users}
        shared = hash_password(password, demo=True)  # one synthetic password for every seed user
        self._hashes = {u.id: shared for u in users}
        # An unknown email still costs one verification, so response time does not reveal
        # which emails exist.
        self._dummy_hash = hash_password(secrets.token_urlsafe(16), demo=True)

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
