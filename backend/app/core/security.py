"""Password hashing and session tokens.

Sessions are a signed JWT in an httpOnly cookie. The token only says who the person is. Their
role and department are always read from the user record on each request, so removing a role
takes effect at once and a token can never carry more power than the record does.
"""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

SESSION_COOKIE = "edss_session"
_ALGORITHM = "HS256"

# Library defaults, for real accounts.
_STANDARD = PasswordHasher()
# Synthetic demo accounts only. A cheaper profile keeps startup and the test suite fast.
_DEMO = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)


def hash_password(password: str, *, demo: bool = False) -> str:
    return (_DEMO if demo else _STANDARD).hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        # the hash carries its own parameters, so either hasher verifies either profile
        return _STANDARD.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def issue_token(user_id: int, secret: str, hours: int, now: datetime | None = None) -> str:
    issued = now or datetime.now(UTC)
    claims = {"sub": str(user_id), "iat": issued, "exp": issued + timedelta(hours=hours)}
    return jwt.encode(claims, secret, algorithm=_ALGORITHM)


def read_token(token: str, secret: str) -> int | None:
    """The user id in a valid, unexpired token, or None. Never raises on a bad token."""
    try:
        claims = jwt.decode(
            token, secret, algorithms=[_ALGORITHM], options={"require": ["exp", "sub"]}
        )
        return int(claims["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
