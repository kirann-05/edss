"""The ingested data in PostgreSQL, written whole and read back into the same `Dataset`.

Nothing above this layer knows where the data lives: the store, the engine and the agents get the
same `Dataset`, `KpiDefinition` and `KpiTarget` objects from here as from the files. Record ids are
written as they are, because approved briefs cite them, and they must never change (D26).

Replacing what is there is allowed only for synthetic data, and refused if any real batch exists:
real data is never wiped silently (docs/DATA_CONTRACT.md section 6). Real data is only ever added,
by app/db/real_data.py. Both are kept side by side and read by mode: once the mode is real, the
synthetic records are still there, archived, but nothing reads them.
"""

from datetime import UTC, date, datetime, time

from sqlalchemy import Connection, func, insert, select, text

from app.db import schema as t
from app.domain.dataset import Dataset
from app.domain.enums import Domain, FactStatus, KpiFramework
from app.domain.models import (
    Department,
    IngestBatch,
    KpiDefinition,
    KpiTarget,
    MetricFact,
    Publication,
    SourceSystem,
)

_DATA_TABLES = (
    "publication_author_dept", "research_publication", "metric_fact", "ingest_batch",
    "source_system", "kpi_target", "kpi_definition",
)  # fmt: skip


class RealDataPresent(RuntimeError):
    """A replace was asked for, and the database holds real data."""


def _midnight(day: date) -> datetime:
    return datetime.combine(day, time(), tzinfo=UTC)


def real_data_present(conn: Connection) -> bool:
    return bool(
        conn.execute(
            select(func.count())
            .select_from(t.ingest_batch)
            .where(t.ingest_batch.c.data_mode == "real")
        ).scalar_one()
    )


def insert_records(conn: Connection, sources, batches, facts, publications) -> None:
    """Add records with the ids they already have. Never updates or removes one."""
    if sources:
        conn.execute(insert(t.source_system), [s.model_dump() for s in sources])
    if not batches:
        return
    conn.execute(
        insert(t.ingest_batch),
        [
            {**b.model_dump(exclude={"finished_at"}), "started_at": _midnight(b.finished_at),
             "finished_at": _midnight(b.finished_at)}
            for b in batches
        ],
    )  # fmt: skip
    now = datetime.now(UTC)
    if facts:
        conn.execute(insert(t.metric_fact), [{**f.model_dump(), "recorded_at": now} for f in facts])
    if publications:
        conn.execute(
            insert(t.research_publication),
            [p.model_dump(exclude={"dept_codes"}) for p in publications],
        )
        conn.execute(
            insert(t.publication_author_dept),
            [
                {"publication_id": p.id, "dept_code": code, "position": i}
                for p in publications
                for i, code in enumerate(p.dept_codes)
            ],
        )


def save_dataset(
    conn: Connection,
    dataset: Dataset,
    definitions: list[KpiDefinition],
    targets: list[KpiTarget],
) -> None:
    """Replace the synthetic data in the database with this dataset, ids and order kept."""
    real = conn.execute(
        select(func.count()).select_from(t.ingest_batch).where(t.ingest_batch.c.data_mode == "real")
    ).scalar_one()
    if real or any(b.data_mode != "synthetic" for b in dataset.batches):
        raise RealDataPresent("only synthetic data may be replaced, and only by synthetic data")

    conn.execute(text(f"truncate {', '.join(_DATA_TABLES)} restart identity"))
    for position, d in enumerate(dataset.departments):
        conn.execute(
            text(
                "insert into department (code, name, school, active, position) "
                "values (:code, :name, :school, :active, :position) on conflict (code) do update "
                "set position = :position, name = case when department.real_position is null "
                "then :name else department.name end, school = case when department.real_position "
                "is null then :school else department.school end"
            ),
            {**d.model_dump(), "position": position},
        )
    insert_records(
        conn, dataset.source_systems, dataset.batches, dataset.facts, dataset.publications
    )
    conn.execute(
        insert(t.kpi_definition),
        [{**d.model_dump(), "domain_tags": [x.value for x in d.domain_tags]} for d in definitions],
    )
    conn.execute(insert(t.kpi_target), [x.model_dump() for x in targets])
    # the next record written without an id must not take one already cited
    for table in ("source_system", "ingest_batch", "metric_fact", "research_publication"):
        conn.execute(
            text(
                f"select setval(pg_get_serial_sequence('{table}', 'id'), "
                f"coalesce((select max(id) from {table}), 0) + 1, false)"
            )
        )
    for key, value in (
        ("dataset_reference_date", dataset.reference_date.isoformat()),
        ("current_period", dataset.current_period),
    ):
        conn.execute(
            text(
                "insert into system_config (key, value) values (:key, :value) "
                "on conflict (key) do update set value = :value"
            ),
            {"key": key, "value": value},
        )


def load_dataset(
    conn: Connection, mode: str = "synthetic"
) -> tuple[Dataset, list[KpiDefinition], list[KpiTarget]]:
    """The records of one data mode, with that mode's list of departments."""
    config = dict(conn.execute(select(t.system_config.c.key, t.system_config.c.value)).all())
    order = t.department.c.real_position if mode == "real" else t.department.c.position
    departments = tuple(
        Department(code=r.code, name=r.name, school=r.school, active=r.active)
        for r in conn.execute(select(t.department).where(order.is_not(None)).order_by(order))
    )
    sources = tuple(
        SourceSystem(id=r.id, name=r.name, owner_office=r.owner_office, kind=r.kind)
        for r in conn.execute(select(t.source_system).order_by(t.source_system.c.id))
    )
    batches = tuple(
        IngestBatch(
            id=r.id, source_system_id=r.source_system_id, data_mode=r.data_mode,
            domain=Domain(r.domain), row_count=r.row_count, rejected_count=r.rejected_count,
            file_ref=r.file_ref, checksum=r.checksum, ingested_by=r.ingested_by,
            finished_at=r.finished_at.astimezone(UTC).date(),
        )
        for r in conn.execute(
            select(t.ingest_batch).where(t.ingest_batch.c.data_mode == mode).order_by(t.ingest_batch.c.id)
        )
    )  # fmt: skip
    in_mode = {b.id for b in batches}
    facts = tuple(
        MetricFact(
            id=r.id, batch_id=r.batch_id, domain=Domain(r.domain), metric_key=r.metric_key,
            dept_code=r.dept_code, period_year=r.period_year, period_sub=r.period_sub,
            value=r.value, numerator=r.numerator, denominator=r.denominator, unit=r.unit,
            status=FactStatus(r.status), as_of=r.as_of, source_system_id=r.source_system_id,
            source_ref=r.source_ref,
        )
        for r in conn.execute(
            select(t.metric_fact).where(t.metric_fact.c.batch_id.in_(in_mode or {-1})).order_by(t.metric_fact.c.id)
        )
    )  # fmt: skip
    credits: dict[int, list[str]] = {}
    for r in conn.execute(
        select(t.publication_author_dept).order_by(
            t.publication_author_dept.c.publication_id, t.publication_author_dept.c.position
        )
    ):
        credits.setdefault(r.publication_id, []).append(r.dept_code)
    publications = tuple(
        Publication(
            id=r.id, batch_id=r.batch_id, dedup_key=r.dedup_key, title=r.title, venue=r.venue,
            period_year=r.period_year, indexing=r.indexing, status=FactStatus(r.status),
            dept_codes=tuple(credits.get(r.id, ())),
        )
        for r in conn.execute(
            select(t.research_publication)
            .where(t.research_publication.c.batch_id.in_(in_mode or {-1}))
            .order_by(t.research_publication.c.id)
        )
    )  # fmt: skip
    periods = tuple(sorted({f.period_year for f in facts} | {p.period_year for p in publications}))
    if not periods:
        raise LookupError(f"the database holds no {mode} records yet")
    if mode == "real":
        # as fresh as the latest reading, and the latest period the university has sent
        reference, current = max(b.finished_at for b in batches), periods[-1]
    else:
        reference = date.fromisoformat(config["dataset_reference_date"])
        current = config.get("current_period") or periods[-1]
    dataset = Dataset(
        reference_date=reference,
        current_period=current,
        periods=periods,
        departments=departments,
        source_systems=sources,
        batches=batches,
        facts=facts,
        publications=publications,
    )
    definitions = [
        KpiDefinition(
            key=r.key, name=r.name, framework=KpiFramework(r.framework), domain=Domain(r.domain),
            domain_tags=tuple(Domain(x) for x in r.domain_tags), formula=r.formula, unit=r.unit,
            higher_is_better=r.higher_is_better, version=r.version, approved_by=r.approved_by,
            approved_on=r.approved_on, active=r.active, placeholder=r.placeholder,
            display_precision=r.display_precision, at_risk_band_pct=r.at_risk_band_pct, note=r.note,
        )
        for r in conn.execute(select(t.kpi_definition).order_by(t.kpi_definition.c.id))
    ]  # fmt: skip
    targets = [
        KpiTarget(
            kpi_key=r.kpi_key, period_year=r.period_year, target_value=r.target_value,
            framework=KpiFramework(r.framework), source_doc=r.source_doc or "",
            placeholder=r.placeholder,
        )
        for r in conn.execute(select(t.kpi_target).order_by(t.kpi_target.c.id))
    ]  # fmt: skip
    return dataset, definitions, targets
