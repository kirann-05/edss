"""A brake on password guessing.

After too many failed sign-ins for one email inside a window, that email is locked for a while,
whatever password is tried. The lock is per email, not per network address, because a campus
shares a few public addresses and one person's typos must not lock out the whole university.

Weakness, said plainly: the counts live in this process. A restart forgets them, and several
server processes would each keep their own. That is fine for one server, and is the place to
move to the database if the deployment grows.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass
class _Record:
    failures: list[datetime] = field(default_factory=list)
    locked_until: datetime | None = None


class LoginThrottle:
    def __init__(
        self,
        *,
        max_failures: int = 5,
        window: timedelta = timedelta(minutes=15),
        lockout: timedelta = timedelta(minutes=15),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._max = max_failures
        self._window = window
        self._lockout = lockout
        self._clock = clock
        self._records: dict[str, _Record] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(email: str) -> str:
        return email.strip().lower()

    def retry_after(self, email: str) -> int | None:
        """Seconds until this email may try again, or None when it may try now."""
        now = self._clock()
        with self._lock:
            record = self._records.get(self._key(email))
            if record is None or record.locked_until is None:
                return None
            if record.locked_until <= now:
                record.locked_until = None
                record.failures.clear()
                return None
            return max(1, int((record.locked_until - now).total_seconds()))

    def failed(self, email: str) -> bool:
        """Count a failure. True when this failure locks the email."""
        now = self._clock()
        with self._lock:
            record = self._records.setdefault(self._key(email), _Record())
            record.failures = [t for t in record.failures if now - t < self._window] + [now]
            if len(record.failures) >= self._max:
                record.locked_until = now + self._lockout
                return True
            return False

    def succeeded(self, email: str) -> None:
        with self._lock:
            self._records.pop(self._key(email), None)
