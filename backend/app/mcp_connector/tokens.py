"""Bearer tokens for the connector, one per run (docs/ARCHITECTURE.md section 4).

A token is minted when a plan is locked and carries exactly the areas that plan may read, plus
reference data every run needs. It expires on its own, and it is revoked when the run ends. The
token is random and means nothing by itself; what it allows lives here, in the process, so a
leaked token is useless once its run is over.
"""

import secrets
import threading
import time
from collections.abc import Callable, Iterable

from mcp.server.auth.provider import AccessToken

from app.domain.enums import Domain

CLIENT_ID = "edss-graph"
REFERENCE = "read:reference"  # calendar, departments, definitions, targets, health, sources


def scope_for(domain: Domain) -> str:
    return f"read:{domain.value}"


class RunTokens:
    """Mints, verifies and revokes run tokens. It is the MCP server's `TokenVerifier`."""

    def __init__(self, ttl_seconds: int = 900, clock: Callable[[], float] = time.time) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._tokens: dict[str, AccessToken] = {}
        self._lock = threading.Lock()

    def mint(self, run_id: str, actor: str, domains: Iterable[Domain]) -> str:
        token = secrets.token_urlsafe(32)
        scopes = sorted({REFERENCE, *(scope_for(d) for d in domains)})
        access = AccessToken(
            token=token,
            client_id=CLIENT_ID,
            scopes=scopes,
            expires_at=int(self._clock()) + self._ttl,
            subject=actor,
            claims={"run_id": run_id},
        )
        with self._lock:
            self._tokens[token] = access
        return token

    def revoke(self, run_id: str) -> None:
        with self._lock:
            self._tokens = {
                t: a for t, a in self._tokens.items() if (a.claims or {}).get("run_id") != run_id
            }

    def lookup(self, token: str) -> AccessToken | None:
        with self._lock:
            access = self._tokens.get(token)
        if access is None or (access.expires_at is not None and access.expires_at <= self._clock()):
            return None
        return access

    async def verify_token(self, token: str) -> AccessToken | None:
        return self.lookup(token)
