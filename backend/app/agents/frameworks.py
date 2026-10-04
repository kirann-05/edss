"""What the drafting node may ask of the framework specialists (Lab 13).

The packs themselves are configuration read from files, so they live outside the agents (see
app/specialists). The graph is handed something that answers these two questions, the same way it
is handed a model and a connector.
"""

from typing import Any, Protocol

from app.domain.enums import KpiFramework


class FrameworkGuide(Protocol):
    def drafting_context(self, framework: KpiFramework) -> dict[str, Any]:
        """Words for the drafter about one framework. Refuses a framework that waits for IQAC."""
        ...

    def pending_labels(self) -> tuple[str, ...]:
        """Frameworks with no approved definitions yet, to be named in every brief."""
        ...
