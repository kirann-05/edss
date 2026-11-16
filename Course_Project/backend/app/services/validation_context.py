"""A validation context built from the connector, for checking a brief that already exists.

The graph builds its own context from the run state while it works. This one serves everything
after the graph: re-checking a person's edit before it is accepted, and showing a stored brief.
Lookups only, which is all the checks need.
"""

from collections.abc import Iterator, Mapping

from app.agents.connector import Connector
from app.agents.models import BriefDocument, Plan
from app.agents.validation.checks import ValidationContext
from app.domain.enums import Domain
from app.domain.models import MetricFact, SourceSystem


class _Facts(Mapping[int, MetricFact]):
    def __init__(self, connector: Connector) -> None:
        self._connector = connector

    def __getitem__(self, fact_id: int) -> MetricFact:
        fact = self._connector.get_fact(fact_id)
        if fact is None:
            raise KeyError(fact_id)
        return fact

    def __iter__(self) -> Iterator[int]:
        return iter(())  # lookup only, the checks never walk every record

    def __len__(self) -> int:
        return 0


class _Sources(Mapping[int, SourceSystem]):
    def __init__(self, connector: Connector) -> None:
        self._connector = connector

    def __getitem__(self, source_id: int) -> SourceSystem:
        source = self._connector.get_source(source_id)
        if source is None:
            raise KeyError(source_id)
        return source

    def __iter__(self) -> Iterator[int]:
        return iter(())

    def __len__(self) -> int:
        return 0


def plan_for(doc: BriefDocument) -> Plan:
    """The slice of the plan the checks need, recovered from the brief itself."""
    return Plan(
        request="",
        period_year=doc.period_year,
        domains=tuple(Domain),
        kpi_keys=doc.plan_kpi_keys,
        options_for=doc.options_for,  # type: ignore[arg-type]
        audience="",
        steps=(),
    )


def context_for_document(
    doc: BriefDocument, connector: Connector, approval_present: bool = False
) -> ValidationContext:
    return ValidationContext(
        plan=plan_for(doc),
        facts=_Facts(connector),
        sources=_Sources(connector),
        publications=tuple(connector.get_publications(doc.period_year)),
        definitions={d.key: d for d in connector.get_kpi_definitions()},
        approval_present=approval_present,
    )
