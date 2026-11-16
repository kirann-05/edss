"""
Lab 7 - every specialist agent shares one contract: `.step(ctx, plan,
connector)` reads what it needs off `ctx`/`connector`, does its one job,
attaches an evidence record (Lab 9) to everything it asserts, and
returns the updated `ctx`. The Coordinator is the only thing that calls
agents; agents never call each other directly.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Evidence:
    """Lab 9 - grounding. Every figure in the final report must trace
    back to one of these."""

    source_system: str
    scope: str
    detail: Dict[str, Any] = field(default_factory=dict)
    in_scope: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source_system": self.source_system,
            "scope": self.scope,
            "detail": self.detail,
            "in_scope": self.in_scope,
        }


class Agent(abc.ABC):
    name: str = "Agent"

    @abc.abstractmethod
    def step(self, ctx, plan, connector) -> Any:
        """Do this agent's one job; return the updated RunContext."""
        ...

    def guardrail_flags(self) -> List[str]:
        """Optional: return human-readable guardrail statements this
        agent enforces, surfaced in the dashboard for transparency."""
        return []
