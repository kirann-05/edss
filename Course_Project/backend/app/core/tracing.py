"""Rule 7: run data never goes to external tracing (no LangSmith or similar).

Observability is the audit table and the run trace UI. This guard runs at startup.
"""

import os
from collections.abc import MutableMapping

TRACING_VARS = ("LANGCHAIN_TRACING_V2", "LANGCHAIN_TRACING", "LANGSMITH_TRACING")
_TRUTHY = {"1", "true", "yes", "on"}


def enforce_no_external_tracing(environ: MutableMapping[str, str] | None = None) -> None:
    """Refuse to start if tracing is switched on, otherwise pin every flag to false.

    Pinning matters because libraries read these variables lazily, long after startup.
    """
    env = os.environ if environ is None else environ
    for var in TRACING_VARS:
        if env.get(var, "").strip().lower() in _TRUTHY:
            raise RuntimeError(
                f"{var} is enabled. EDSS never sends run data to external tracing (rule 7)."
            )
    for var in TRACING_VARS:
        env[var] = "false"
