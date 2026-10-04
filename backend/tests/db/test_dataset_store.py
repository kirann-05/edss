"""L5c: the sample goes into PostgreSQL and comes back the same, with every planted trap in it."""

from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text

from app.db.dataset_store import RealDataPresent, load_dataset, save_dataset
from app.ingestion.manifest import ingest_folder
from app.kpi.loader import load_seed_definitions, load_seed_targets
from app.services.store import DataStore
from app.synthetic.traps import observe

pytestmark = pytest.mark.db
REFERENCE = date(2026, 10, 1)
SAMPLE = Path(__file__).parents[3] / "data" / "sample"


@pytest.fixture(scope="module")
def stored(migrated):
    dataset = ingest_folder(SAMPLE, REFERENCE, data_mode="synthetic").ledger.dataset()
    definitions, targets = load_seed_definitions(), load_seed_targets()
    with migrated.begin() as conn:
        save_dataset(conn, dataset, definitions, targets)
    with migrated.connect() as conn:
        back = load_dataset(conn)
    return (dataset, definitions, targets), back


def test_everything_comes_back_exactly_ids_order_and_decimals_included(stored):
    (dataset, definitions, targets), (d2, def2, tar2) = stored
    assert d2 == dataset
    assert def2 == definitions and tar2 == targets
    assert [str(f.value) for f in d2.facts] == [str(f.value) for f in dataset.facts]


def test_every_planted_trap_is_found_in_what_the_database_gives_back(stored):
    dataset, definitions, targets = stored[1]
    traps = observe(DataStore(dataset, definitions, targets, REFERENCE, 90))
    assert len(traps) >= 10 and all(t.ok for t in traps), [t for t in traps if not t.ok]


def test_the_data_traps_can_be_seen_by_plain_query(stored, migrated):
    current = stored[0][0].current_period
    with migrated.connect() as conn:
        q = lambda sql: conn.execute(text(sql), {"p": current}).scalar_one()  # noqa: E731
        stale = q(
            "select count(distinct dept_code) from metric_fact where domain = 'placement' "
            "and period_year = :p and as_of < date '2026-10-01' - 120"
        )
        no_research = q(
            "select count(*) from department d where not exists (select 1 from metric_fact f "
            "where f.dept_code = d.code and f.domain = 'research' and f.period_year = :p)"
        )
        forecast = q(
            "select count(*) from metric_fact where metric_key = 'fin.revenue_forecast' "
            "and period_year = :p and status = 'forecast'"
        )
        unreconciled = q(
            "select count(*) from metric_fact where status = 'pending_reconciliation' and period_year = :p"
        )
        shared = q(
            "select count(*) from (select publication_id from publication_author_dept "
            "group by publication_id having count(*) > 1) s"
        )
        provisional = q(
            "select count(*) from metric_fact where metric_key = 'plc.offers_provisional' and period_year = :p"
        )
    assert (stale, no_research, unreconciled) == (1, 1, 1)  # T1, T2, T8
    assert forecast > 0 and shared > 0 and provisional > 0  # T4, T5, T3


def test_real_data_is_never_replaced(stored, migrated):
    dataset, definitions, targets = stored[0]
    with migrated.begin() as conn:
        conn.execute(text("update ingest_batch set data_mode = 'real' where id = 1"))
    try:
        with pytest.raises(RealDataPresent), migrated.begin() as conn:
            save_dataset(conn, dataset, definitions, targets)
    finally:
        with migrated.begin() as conn:
            conn.execute(text("update ingest_batch set data_mode = 'synthetic' where id = 1"))
