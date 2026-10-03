"""FakeLLM: a deterministic stand-in for a language model (CHECKLIST C3, decision C3).

It is not random and not a recording. Each task has a handler that reads the structured input
and returns structured output, the way the real model will. That keeps every test and the
whole graph runnable offline and identical on every run, and gives the demo a safe fallback.

It is always labelled. The UI shows "Drafts are canned" whenever it is the provider, so nobody
mistakes its text for a model's. Handlers are registered by the skills that own each task
(see app/agents/skills).
"""

from collections.abc import Callable
from typing import Any

Handler = Callable[[dict[str, Any]], dict[str, Any]]

_HANDLERS: dict[str, Handler] = {}


def register(task: str) -> Callable[[Handler], Handler]:
    """Register the canned handler for one task name."""

    def decorator(handler: Handler) -> Handler:
        _HANDLERS[task] = handler
        return handler

    return decorator


class FakeLLM:
    """Always local, so it needs no data-mode guard. It never leaves the machine."""

    provider = "fake"

    def __init__(self, role: str = "drafter") -> None:
        self.role = role
        self.name = f"fake-{role}"

    def complete(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            handler = _HANDLERS[task]
        except KeyError:
            raise KeyError(f"FakeLLM has no handler for task {task!r}") from None
        return handler(payload)

    def generate(self, task: str, payload: dict[str, Any], schema: Any, max_repairs: int = 2):
        from app.agents.llm import structured_call

        return structured_call(self, task, payload, schema, max_repairs)
