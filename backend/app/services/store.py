"""In-memory data store: the synthetic dataset plus the KPI engine's results.

This is the interim implementation of decision D22. Routers and views only call these methods,
so the Postgres version (CHECKLIST F3) replaces this one file and nothing above it changes.
It is built from the synthetic generator only, and refuses to stand in for real data.
"""

from datetime import date

from app.domain.enums import Domain
from app.domain.models import (
    Department,
    IngestBatch,
    KpiDefinition,
    KpiTarget,
    MetricFact,
    SourceSystem,
)
from app.kpi.engine import PeriodData, compute_all
from app.kpi.loader import load_seed_definitions, load_seed_targets
from app.kpi.results import KpiResult
from app.synthetic.generator import SyntheticDataset, generate


class UnknownPeriodError(KeyError):
    pass


class UnknownKpiError(KeyError):
    pass


class DataStore:
    def __init__(
        self,
        dataset: SyntheticDataset,
        definitions: list[KpiDefinition],
        targets: list[KpiTarget],
        today: date,
        stale_after_days: int,
    ) -> None:
        self.dataset = dataset
        self.today = today
        self.stale_after_days = stale_after_days
        self.definitions = tuple(d for d in definitions if d.active)
        self._definition_by_key = {d.key: d for d in self.definitions}
        self._target = {(t.kpi_key, t.period_year): t for t in targets}
        self.departments: dict[str, Department] = {d.code: d for d in dataset.departments}
        self.facts_by_id: dict[int, MetricFact] = {f.id: f for f in dataset.facts}
        self.batches: dict[int, IngestBatch] = {b.id: b for b in dataset.batches}
        self.sources: dict[int, SourceSystem] = {s.id: s for s in dataset.source_systems}
        self._results: dict[str, dict[str, KpiResult]] = {}

    @classmethod
    def build(cls, today: date, stale_after_days: int) -> "DataStore":
        """Synthetic data stamped relative to `today`, so the demo is current the day it starts."""
        return cls(
            generate(reference_date=today),
            load_seed_definitions(),
            load_seed_targets(),
            today,
            stale_after_days,
        )

    # periods --------------------------------------------------------------------------------
    @property
    def periods(self) -> tuple[str, ...]:
        return self.dataset.periods

    @property
    def current_period(self) -> str:
        return self.dataset.current_period

    def resolve_period(self, period: str | None) -> str:
        chosen = period or self.current_period
        if chosen not in self.periods:
            raise UnknownPeriodError(chosen)
        return chosen

    def period_data(self, period: str) -> PeriodData:
        return PeriodData(
            period_year=period,
            departments=self.dataset.departments,
            facts=tuple(f for f in self.dataset.facts if f.period_year == period),
            publications=tuple(p for p in self.dataset.publications if p.period_year == period),
            is_current=period == self.current_period,
        )

    # kpis -----------------------------------------------------------------------------------
    def definition(self, key: str) -> KpiDefinition:
        try:
            return self._definition_by_key[key]
        except KeyError:
            raise UnknownKpiError(key) from None

    def target(self, key: str, period: str) -> KpiTarget | None:
        return self._target.get((key, period))

    def results(self, period: str) -> dict[str, KpiResult]:
        """Every active KPI for one period, in definition order. Computed once, then cached."""
        if period not in self._results:
            targets = {k: t for (k, p), t in self._target.items() if p == period}
            computed = compute_all(
                self.definitions,
                targets,
                self.period_data(period),
                self.today,
                self.stale_after_days,
            )
            self._results[period] = {r.kpi_key: r for r in computed}
        return self._results[period]

    def result(self, key: str, period: str) -> KpiResult:
        self.definition(key)  # raises UnknownKpiError for a key we do not know
        return self.results(period)[key]

    # facts ----------------------------------------------------------------------------------
    def facts(
        self, period: str, dept: str | None = None, domain: Domain | None = None
    ) -> list[MetricFact]:
        return [
            f
            for f in self.dataset.facts
            if f.period_year == period
            and (dept is None or f.dept_code == dept)
            and (domain is None or f.domain is domain)
        ]
