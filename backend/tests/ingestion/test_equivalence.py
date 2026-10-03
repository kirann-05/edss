"""The adapter swap (docs/BUILD_PLAN.md day 3): change where the data comes from, change nothing else.

The synthetic dataset is written out as the files an office would send, read back through the CSV
adapter, and then again through the SQL adapter. Every KPI for every period must come out exactly
as it did from the original, down to the unrounded decimal, the status, the flags and the records
each figure rests on. If any of this differs, the adapters or the validator change the data, and
nothing built on them can be trusted.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.domain.dataset import Dataset
from app.domain.enums import Domain
from app.ingestion.adapters import SqlAdapter, read_only_sqlite
from app.ingestion.loader import Ledger
from app.ingestion.manifest import ingest_folder, read_departments
from app.ingestion.rows import FACT_REQUIRED, PUBLICATION_REQUIRED
from app.kpi.loader import load_seed_definitions, load_seed_targets
from app.main import create_app
from app.services.store import DataStore
from tests.api.conftest import EMAILS, PASSWORD, REF, make_settings

from .conftest import TODAY, sqlite_with

DOMAINS = (Domain.ACADEMIC, Domain.RESEARCH, Domain.PLACEMENT, Domain.FINANCE, Domain.REFERENCE)


def store_of(dataset: Dataset) -> DataStore:
    return DataStore(dataset, load_seed_definitions(), load_seed_targets(), TODAY, 90)


def slots(store: DataStore, ids) -> list[tuple]:
    """Records are named by what they are, because the numbers given to them differ between loads."""
    return sorted(
        (
            f.dept_code,
            f.metric_key,
            f.period_year,
            f.period_sub,
            str(f.value),
            f.status.value,
            str(f.as_of),
        )
        for f in (store.facts_by_id[i] for i in ids)
    )


def project(store: DataStore, period: str) -> dict:
    out = {}
    for key, r in store.results(period).items():
        out[key] = {
            "value": r.value, "target": r.target, "variance": r.variance_abs, "status": r.status,
            "flags": (r.flags.stale_departments, r.flags.missing_departments, r.flags.excluded_departments,
                      r.flags.undefined_departments, r.flags.no_target, len(r.flags.excluded_fact_ids)),
            "as_of": r.as_of,
            "inputs": [(i.label, i.value) for i in r.inputs],
            "records": slots(store, r.input_fact_ids),
            "departments": [(d.dept_code, d.state, d.value, d.stale, d.as_of, d.reason, slots(store, d.input_fact_ids)) for d in r.departments],
        }  # fmt: skip
    return out


@pytest.fixture(scope="module")
def original(dataset) -> DataStore:
    return store_of(dataset)


@pytest.fixture(scope="module")
def from_csv(exported) -> DataStore:
    outcome = ingest_folder(exported, TODAY, data_mode="synthetic")
    assert outcome.errors == [] and outcome.rejected == 0, outcome.errors
    return store_of(outcome.ledger.dataset())


@pytest.fixture(scope="module")
def from_sql(tmp_path_factory, exported, dataset) -> DataStore:
    database = sqlite_with(tmp_path_factory.mktemp("db"), exported)
    ledger = Ledger(read_departments(exported / "departments.csv"), TODAY, data_mode="synthetic")
    source = ledger.source("University ERP views", "IT cell", "sql")

    def connect():
        return sqlite3.connect(database)

    for domain in DOMAINS:
        adapter = SqlAdapter(
            connect,
            f"SELECT * FROM v_{domain.value}",
            view=f"v_{domain.value}",
            required=FACT_REQUIRED,
            make_read_only=read_only_sqlite,
        )
        result = ledger.ingest_facts(adapter, source, domain, "test")
        assert result.rejects == (), (domain, result.rejects[:3])
    pubs = SqlAdapter(
        connect,
        "SELECT * FROM v_publications",
        view="v_publications",
        required=PUBLICATION_REQUIRED,
        make_read_only=read_only_sqlite,
    )
    assert ledger.ingest_publications(pubs, source, "test").rejects == ()
    return store_of(ledger.dataset())


class TestSameDataWhereverItCameFrom:
    @pytest.mark.parametrize("period", ["2023-24", "2024-25", "2025-26"])
    def test_every_kpi_from_csv_files_equals_the_original(self, original, from_csv, period):
        assert project(from_csv, period) == project(original, period)

    @pytest.mark.parametrize("period", ["2023-24", "2024-25", "2025-26"])
    def test_every_kpi_from_a_sql_source_equals_the_original(self, original, from_sql, period):
        assert project(from_sql, period) == project(original, period)

    def test_the_comparison_can_fail(self, original, from_csv):
        # a positive control: change one figure in the period being compared, and it must show
        target = next(
            f for f in from_csv.dataset.facts
            if (f.period_year, f.dept_code, f.metric_key) == ("2025-26", "CSE", "acad.students_passed")
        )  # fmt: skip
        changed = [
            f.model_copy(update={"value": f.value + 1}) if f.id == target.id else f
            for f in from_csv.dataset.facts
        ]
        tampered = store_of(Dataset(**{**from_csv.dataset.__dict__, "facts": tuple(changed)}))
        assert project(tampered, "2025-26") != project(original, "2025-26")
        assert project(tampered, "2023-24") == project(original, "2023-24")  # and only that period

    def test_the_planted_traps_survive_the_trip(self, from_csv):
        pl = from_csv.result("PL_PCT", "2025-26")
        assert str(pl.value).startswith("74.96") and pl.status.value == "missed"  # T6
        assert "CIVIL" in pl.flags.stale_departments  # T1
        assert "AIML" in pl.flags.undefined_departments  # T9
        assert "MECH" in from_csv.result("RS_PUB_PF", "2025-26").flags.missing_departments  # T2
        assert "BIOTECH" in from_csv.result("FN_UTIL", "2025-26").flags.excluded_departments  # T8

    def test_a_shared_paper_is_still_one_paper_credited_to_both(self, original, from_csv):
        shared = [p for p in from_csv.dataset.publications if len(p.dept_codes) > 1]
        assert len(from_csv.dataset.publications) == len(original.dataset.publications)
        assert sorted((p.dedup_key, p.dept_codes) for p in shared) == sorted(
            (p.dedup_key, p.dept_codes)
            for p in original.dataset.publications
            if len(p.dept_codes) > 1
        )

    def test_the_sources_and_their_owners_travel_with_the_data(self, from_csv, original):
        assert {(s.name, s.owner_office) for s in from_csv.dataset.source_systems} == {
            (s.name, s.owner_office) for s in original.dataset.source_systems
        }


class TestNothingAboveTheAdapterChanges:
    """The API, and the agents behind it, run unchanged over the ingested data (rule 6)."""

    def login(self, store: DataStore) -> TestClient:
        app = create_app(make_settings(), today=REF, synchronous_runs=True, store=store)
        client = TestClient(app)
        assert (
            client.post(
                "/api/auth/login", json={"email": EMAILS["registrar"], "password": PASSWORD}
            ).status_code
            == 200
        )
        return client

    def test_the_dashboard_figures_are_identical(self, original, from_csv, from_sql):
        wanted = self.login(original).get("/api/kpis").json()["kpis"]
        for store in (from_csv, from_sql):
            got = self.login(store).get("/api/kpis").json()["kpis"]
            assert [(k["key"], k["value"], k["target"], k["status"]) for k in got] == [
                (k["key"], k["value"], k["target"], k["status"]) for k in wanted
            ]

    def test_a_run_over_ingested_data_reaches_the_gate_with_the_same_validated_brief(
        self, original, from_csv
    ):
        def brief_of(store):
            client = self.login(store)
            run = client.post(
                "/api/runs", json={"request": "Governing Council brief for 2025-26 on everything"}
            ).json()
            client.post(f"/api/runs/{run['id']}/plan/lock", json={"faults": []})
            finished = client.get(f"/api/runs/{run['id']}").json()
            assert finished["status"] == "awaiting_review", finished
            return client.get(f"/api/briefs/{finished['brief_id']}").json()

        a, b = brief_of(original), brief_of(from_csv)
        assert a["validation"]["passed"] and b["validation"]["passed"]
        assert [(k["key"], k["value"], k["status"]) for k in a["document"]["kpis"]] == [
            (k["key"], k["value"], k["status"]) for k in b["document"]["kpis"]
        ]
        assert [s["kpi_key"] for s in a["document"]["option_sets"]] == [
            s["kpi_key"] for s in b["document"]["option_sets"]
        ]
