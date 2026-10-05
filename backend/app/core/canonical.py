"""One canonical text form for anything that gets hashed or logged.

The audit chain and the runtime wrapper both need the same content to produce the same text
whatever the key order or the type of number, so they share this single implementation.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


def _default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")  # text, never a float, so a figure hashes the same everywhere
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=str)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"cannot serialise a value of type {type(value).__name__}")


def canonical(value: Any) -> str:
    """One text form per content, whatever the key order, so the same facts always hash alike."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_default)
