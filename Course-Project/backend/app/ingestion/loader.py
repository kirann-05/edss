"""The ledger: what has been ingested, batch by batch, and the dataset that results.

Each ingest is one immutable batch. Re-ingesting a file with the same checksum changes nothing.
A changed file is a new batch, and for any slot it covers the newest batch supplies the figure,
while the older rows stay so that evidence cited in an approved brief keeps resolving.

Two papers listed under two departments with the same DOI become one publication credited to
both, which is what lets the institution count it once (docs/DATA_CONTRACT.md, trap T5).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.dataset import Dataset
from app.domain.enums import Domain, FactStatus
from app.domain.models import Department, IngestBatch, MetricFact, Publication, SourceSystem
from app.ingestion.adapters import SourceAdapter
from app.ingestion.validator import (
    PublicationRow,
    Reject,
    validate_facts,
    validate_publications,
)


@dataclass(frozen=True)
class IngestResult:
    batch: IngestBatch
    accepted: int
    rejects: tuple[Reject, ...]
    noop: bool = False  # the same content was ingested before, so nothing was added


class Ledger:
    def __init__(
        self, departments: Sequence[Department], today: date, data_mode: str = "real"
    ) -> None:
        self.departments = tuple(departments)
        self.today = today
        self.data_mode = data_mode
        self.sources: list[SourceSystem] = []
        self.batches: list[IngestBatch] = []
        self.facts: list[MetricFact] = []
        self.publications: list[Publication] = []
        self._known_content: dict[tuple[str, str, str], int] = {}
        # the highest ids already used elsewhere, so a ledger restored from the database never
        # gives a new record an id that an approved brief already cites (D26)
        self._floor = {"source": 0, "batch": 0, "fact": 0, "publication": 0}

    @classmethod
    def restored(
        cls,
        departments: Sequence[Department],
        today: date,
        data_mode: str,
        *,
        sources: Sequence[SourceSystem],
        batches: Sequence[IngestBatch],
        facts: Sequence[MetricFact],
        publications: Sequence[Publication],
        floors: dict[str, int],
    ) -> "Ledger":
        """A ledger that carries on from what the database holds: unchanged files add nothing,
        changed files become new batches, and new ids start above every id already used."""
        ledger = cls(departments, today, data_mode)
        ledger.sources = list(sources)
        ledger.batches = list(batches)
        ledger.facts = list(facts)
        ledger.publications = list(publications)
        ledger._floor.update(floors)
        names = {s.id: s.name for s in sources}
        publication_batches = {p.batch_id for p in publications}
        for batch in batches:
            label = "publications" if batch.id in publication_batches else batch.domain.value
            ledger._known_content[(names[batch.source_system_id], label, batch.checksum)] = batch.id
        return ledger

    def _next(self, kind: str, used: Sequence) -> int:
        return max([self._floor[kind], *(item.id for item in used)]) + 1

    # --- sources --------------------------------------------------------------------------------
    def source(self, name: str, owner_office: str, kind: str) -> SourceSystem:
        for existing in self.sources:
            if existing.name == name:
                return existing
        created = SourceSystem(
            id=self._next("source", self.sources), name=name, owner_office=owner_office, kind=kind
        )
        self.sources.append(created)
        return created

    def _batch(
        self, source: SourceSystem, domain: Domain, rows: int, rejected: int, adapter: SourceAdapter,
        checksum: str, ingested_by: str,
    ) -> IngestBatch:  # fmt: skip
        batch = IngestBatch(
            id=self._next("batch", self.batches),
            source_system_id=source.id,
            data_mode=self.data_mode,
            domain=domain,
            row_count=rows,
            rejected_count=rejected,
            file_ref=adapter.file_ref,
            checksum=checksum,
            ingested_by=ingested_by,
            finished_at=self.today,
        )
        self.batches.append(batch)
        return batch

    def _seen(self, source: SourceSystem, label: str, checksum: str) -> IngestBatch | None:
        batch_id = self._known_content.get((source.name, label, checksum))
        return next((b for b in self.batches if b.id == batch_id), None)

    # --- facts ----------------------------------------------------------------------------------
    def ingest_facts(
        self, adapter: SourceAdapter, source: SourceSystem, domain: Domain, ingested_by: str
    ) -> IngestResult:
        checksum = adapter.checksum()
        earlier = self._seen(source, domain.value, checksum)
        if earlier is not None:
            return IngestResult(earlier, 0, (), noop=True)

        rows = adapter.read()
        accepted, rejects = validate_facts(
            rows, domain, {d.code for d in self.departments}, self.today
        )
        batch = self._batch(
            source, domain, len(accepted), len(rejects), adapter, checksum, ingested_by
        )
        start = self._next("fact", self.facts) - 1
        for offset, row in enumerate(accepted, start=1):
            self.facts.append(
                MetricFact(
                    id=start + offset, batch_id=batch.id, domain=domain, metric_key=row.metric_key,
                    dept_code=row.dept_code, period_year=row.period_year, period_sub=row.period_sub,
                    value=row.value, numerator=row.numerator, denominator=row.denominator, unit=row.unit,
                    status=row.status, as_of=row.as_of, source_system_id=source.id, source_ref=row.source_ref,
                )
            )  # fmt: skip
        self._known_content[(source.name, domain.value, checksum)] = batch.id
        return IngestResult(batch, len(accepted), tuple(rejects))

    # --- publications ---------------------------------------------------------------------------
    def ingest_publications(
        self, adapter: SourceAdapter, source: SourceSystem, ingested_by: str
    ) -> IngestResult:
        checksum = adapter.checksum()
        earlier = self._seen(source, "publications", checksum)
        if earlier is not None:
            return IngestResult(earlier, 0, (), noop=True)

        rows = adapter.read()
        accepted, rejects = validate_publications(rows, {d.code for d in self.departments})
        batch = self._batch(
            source, Domain.RESEARCH, len(accepted), len(rejects), adapter, checksum, ingested_by
        )

        merged: dict[tuple[str, str], PublicationRow] = {}
        for row in accepted:
            slot = (row.dedup_key, row.period_year)
            held = merged.get(slot)
            if held is None:
                merged[slot] = row
                continue
            # the same paper listed under another department: one paper, credit to both
            credit = tuple(dict.fromkeys((*held.dept_codes, *row.dept_codes)))
            # a figure is only as final as its least final listing (rule 4)
            status = (
                held.status
                if held.status not in _ACTUAL
                else row.status
                if row.status not in _ACTUAL
                else held.status
            )
            merged[slot] = PublicationRow(
                ref=held.ref, dedup_key=held.dedup_key, title=held.title, venue=held.venue,
                period_year=held.period_year, indexing=held.indexing, status=status, dept_codes=credit,
            )  # fmt: skip
        start = self._next("publication", self.publications) - 1
        for offset, row in enumerate(merged.values(), start=1):
            self.publications.append(
                Publication(
                    id=start + offset, batch_id=batch.id, dedup_key=row.dedup_key, title=row.title,
                    venue=row.venue, period_year=row.period_year, indexing=row.indexing,
                    status=row.status, dept_codes=row.dept_codes,
                )
            )  # fmt: skip
        self._known_content[(source.name, "publications", checksum)] = batch.id
        return IngestResult(batch, len(accepted), tuple(rejects))

    # --- the result -----------------------------------------------------------------------------
    def dataset(self, current_period: str | None = None) -> Dataset:
        periods = tuple(
            sorted({f.period_year for f in self.facts} | {p.period_year for p in self.publications})
        )
        if not periods:
            raise ValueError("nothing has been ingested yet, so there is no period to report on")
        return Dataset(
            reference_date=self.today,
            current_period=current_period or periods[-1],
            periods=periods,
            departments=self.departments,
            source_systems=tuple(self.sources),
            batches=tuple(self.batches),
            facts=tuple(self.facts),
            publications=tuple(self.publications),
        )


_ACTUAL = (FactStatus.FINAL, FactStatus.AUDITED)
