"""A set of departments, sources, batches, facts and publications: what the engine reads.

The synthetic generator builds one, and so does the ingestion layer from real files. The engine
and the store neither know nor care which. Facts are immutable and belong to a batch. A newer
batch for the same slot supersedes an older one for new figures, and the older rows stay, because
a brief approved last month cites their ids and those must keep resolving (docs/ARCHITECTURE.md
principle 3).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.domain.models import (
    Department,
    IngestBatch,
    MetricFact,
    Publication,
    SourceSystem,
)


@dataclass(frozen=True)
class Dataset:
    reference_date: date
    current_period: str
    periods: tuple[str, ...]
    departments: tuple[Department, ...]
    source_systems: tuple[SourceSystem, ...]
    batches: tuple[IngestBatch, ...]
    facts: tuple[MetricFact, ...]  # every fact ever ingested, superseded ones included
    publications: tuple[Publication, ...]


def current_facts(facts: Iterable[MetricFact]) -> tuple[MetricFact, ...]:
    """One fact per slot: the one from the newest batch. Order is kept as ingested."""
    newest: dict[tuple[str, str, str, str], MetricFact] = {}
    for fact in facts:
        slot = (fact.dept_code, fact.metric_key, fact.period_year, fact.period_sub)
        held = newest.get(slot)
        if held is None or fact.batch_id >= held.batch_id:
            newest[slot] = fact
    keep = {f.id for f in newest.values()}
    return tuple(f for f in facts if f.id in keep)  # type: ignore[union-attr]
