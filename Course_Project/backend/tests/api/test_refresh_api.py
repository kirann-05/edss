"""Refreshing the data (FR-16): read the sources again, change nothing that was already cited."""

import csv
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ingestion.export import export_dataset
from app.main import create_app
from app.synthetic.generator import generate

from ..ingestion.conftest import TODAY
from .conftest import EMAILS, PASSWORD, make_settings


def sign_in(app, persona="registrar") -> TestClient:
    client = TestClient(app)
    assert (
        client.post(
            "/api/auth/login", json={"email": EMAILS[persona], "password": PASSWORD}
        ).status_code
        == 200
    )
    return client


@pytest.fixture
def folder(tmp_path) -> Path:
    target = tmp_path / "drop"
    export_dataset(generate(reference_date=TODAY), target)
    return target


@pytest.fixture
def app(folder):
    return create_app(make_settings(ingest_dir=str(folder)), today=TODAY, synchronous_runs=True)


def edit(folder: Path, filename: str, where, change) -> int:
    """Change the rows that match, and say how many did. A test never has to guess."""
    path = folder / filename
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    header, changed = rows[0], 0
    for row in rows[1:]:
        record = dict(zip(header, row, strict=True))
        if where(record):
            change(record)
            row[:] = [record[c] for c in header]
            changed += 1
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    return changed


class TestWhoMayRefresh:
    @pytest.mark.parametrize("persona", ["registrar", "admin"])
    def test_the_registrar_and_the_administrator_may(self, app, persona):
        assert sign_in(app, persona).post("/api/data/refresh").status_code == 200

    @pytest.mark.parametrize("persona", ["principal", "dean", "hod_cse", "viewer"])
    def test_nobody_else_may(self, app, persona):
        assert sign_in(app, persona).post("/api/data/refresh").status_code == 403

    def test_it_needs_a_session(self, app):
        assert TestClient(app).post("/api/data/refresh").status_code == 401


class TestRefreshingAFolder:
    def test_nothing_changed_means_nothing_added_and_the_response_says_so(self, app):
        client = sign_in(app)
        before = client.get("/api/kpis").json()["kpis"]
        body = client.post("/api/data/refresh").json()
        assert body["source"] == "folder" and body["rejected"] == 0
        assert body["unchanged_files"] == 6  # five areas of facts and the paper register
        assert body["accepted"] == 0
        assert client.get("/api/kpis").json()["kpis"] == before

    def test_a_changed_file_changes_the_figures_from_then_on(self, app, folder):
        client = sign_in(app)
        before = next(k for k in client.get("/api/kpis").json()["kpis"] if k["key"] == "PL_PCT")
        edit(
            folder, "placement.csv",
            lambda r: (r["dept_code"], r["metric_key"], r["period_year"]) == ("CSE", "plc.placed_confirmed", "2025-26"),
            lambda r: r.update(value=str(int(r["value"]) - 40)),
        )  # fmt: skip
        body = client.post("/api/data/refresh").json()
        assert (
            body["rejected"] == 0 and body["accepted"] > 0 and body["unchanged_files"] == 5
        )  # only placement changed
        after = next(k for k in client.get("/api/kpis").json()["kpis"] if k["key"] == "PL_PCT")
        assert float(after["value"]) < float(before["value"])

    def test_a_record_cited_before_the_refresh_is_still_the_same_record_after_it(self, app, folder):
        client = sign_in(app)
        state = app.state.edss
        cited = next(
            f
            for f in state.store.facts("2025-26", dept="CSE")
            if f.metric_key == "plc.placed_confirmed"
        )
        edit(
            folder, "placement.csv",
            lambda r: (r["dept_code"], r["metric_key"], r["period_year"]) == ("CSE", "plc.placed_confirmed", "2025-26"),
            lambda r: r.update(value="1"),
        )  # fmt: skip
        assert client.post("/api/data/refresh").status_code == 200
        # the id an approved brief may hold still resolves, to the figure it was written from
        assert client.get(f"/api/facts/{cited.id}").json()["value"] == str(cited.value)
        # and the figure now in use is a different record, with a different id
        current = next(
            f
            for f in app.state.edss.store.facts("2025-26", dept="CSE")
            if f.metric_key == "plc.placed_confirmed"
        )
        assert current.id != cited.id and str(current.value) == "1"

    def test_the_old_record_is_marked_as_not_used_and_the_new_one_as_used(self, app, folder):
        client = sign_in(app)
        old = next(
            f
            for f in app.state.edss.store.facts("2025-26", dept="CSE")
            if f.metric_key == "plc.placed_confirmed"
        )
        edit(folder, "placement.csv", lambda r: (r["dept_code"], r["metric_key"], r["period_year"]) == ("CSE", "plc.placed_confirmed", "2025-26"), lambda r: r.update(value="5"))  # fmt: skip
        client.post("/api/data/refresh")
        assert client.get(f"/api/facts/{old.id}").status_code == 200

    def test_rows_that_break_the_contract_are_refused_with_where_and_why_and_the_rest_is_used(
        self, app, folder
    ):
        client = sign_in(app)
        broken = edit(
            folder, "academic.csv",
            lambda r: r["dept_code"] == "CSE" and r["metric_key"] == "acad.courses_total",
            lambda r: r.update(status=""),
        )  # fmt: skip
        assert broken > 0
        body = client.post("/api/data/refresh").json()
        assert body["rejected"] == broken and body["accepted"] > 0
        assert body["rejects"][0]["why"] == ["the status is missing"]
        assert body["rejects"][0]["where"].startswith("academic.csv:row")

    def test_an_unreadable_file_leaves_the_data_in_use_untouched_and_says_why(self, app, folder):
        client = sign_in(app)
        before = client.get("/api/kpis").json()
        (folder / "finance.csv").write_text("dept_code,value\nCSE,1\n")
        response = client.post("/api/data/refresh")
        assert response.status_code == 422 and "finance" in response.json()["detail"]
        assert client.get("/api/kpis").json() == before

    def test_a_refresh_and_a_failed_refresh_are_both_in_the_audit_log(self, app, folder):
        client = sign_in(app)
        client.post("/api/data/refresh")
        (folder / "finance.csv").write_text("dept_code\n")
        client.post("/api/data/refresh")
        actions = [r.action for r in app.state.edss.audit.rows()]
        assert "data.refresh" in actions and "data.refresh_failed" in actions

    def test_a_changed_list_of_departments_needs_a_restart_and_is_refused(self, app, folder):
        client = sign_in(app)
        with (folder / "departments.csv").open("a", newline="") as handle:
            csv.writer(handle).writerow(["PHYS", "Physics", "Science"])
        response = client.post("/api/data/refresh")
        assert response.status_code == 422 and "restart" in response.json()["detail"]

    def test_a_refresh_is_refused_while_a_run_is_in_progress(self, app):
        from app.services.runs import RunStatus

        client = sign_in(app)
        run = client.post("/api/runs", json={"request": "Prepare the leadership brief"}).json()
        app.state.edss.runs.get(run["id"]).status = RunStatus.RUNNING
        assert client.post("/api/data/refresh").status_code == 409

    def test_a_new_run_after_a_refresh_uses_the_new_data(self, app, folder):
        client = sign_in(app)
        edit(folder, "placement.csv", lambda r: (r["dept_code"], r["metric_key"], r["period_year"]) == ("CSE", "plc.placed_confirmed", "2025-26"), lambda r: r.update(value="100"))  # fmt: skip
        client.post("/api/data/refresh")
        run = client.post(
            "/api/runs", json={"request": "Placement brief for the Principal for 2025-26"}
        ).json()
        client.post(f"/api/runs/{run['id']}/plan/lock", json={"faults": []})
        brief_id = client.get(f"/api/runs/{run['id']}").json()["brief_id"]
        figure = next(
            k
            for k in client.get(f"/api/briefs/{brief_id}").json()["document"]["kpis"]
            if k["key"] == "PL_PCT"
        )
        assert (
            figure["value"]
            == next(k for k in client.get("/api/kpis").json()["kpis"] if k["key"] == "PL_PCT")[
                "value"
            ]
        )


class TestRefreshingTheSyntheticSet:
    def test_it_restamps_the_dates_and_reports_the_source(self):
        app = create_app(make_settings(), today=TODAY, synchronous_runs=True)
        body = sign_in(app).post("/api/data/refresh").json()
        assert body["source"] == "synthetic" and body["folder"] is None and body["rejected"] == 0
        assert body["current_period"] == "2025-26" and body["periods"] == [
            "2023-24",
            "2024-25",
            "2025-26",
        ]


def test_an_app_started_on_a_folder_with_an_unreadable_file_refuses_to_start(tmp_path):
    folder = tmp_path / "drop"
    shutil.copytree(
        Path(__file__).resolve().parents[3] / "data" / "sample",
        folder,
        ignore=shutil.ignore_patterns("templates"),
    )
    (folder / "academic.csv").write_text("dept_code\n")
    with pytest.raises(Exception, match="academic"):
        create_app(make_settings(ingest_dir=str(folder)), today=TODAY)
