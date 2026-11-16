"""A folder of exports and its manifest, and the report a data owner reads."""

import shutil
from pathlib import Path

import pytest
import yaml

from app.ingestion.manifest import ManifestError, ingest_folder, read_departments
from app.ingestion.reconcile import reconciliation_report

from .conftest import TODAY, fact, fact_file, write_csv


@pytest.fixture
def folder(tmp_path, exported) -> Path:
    target = tmp_path / "drop"
    shutil.copytree(exported, target)
    return target


def edit_manifest(folder: Path, change):
    path = folder / "manifest.yml"
    manifest = yaml.safe_load(path.read_text())
    change(manifest)
    path.write_text(yaml.safe_dump(manifest))


class TestFolder:
    def test_a_whole_folder_is_read_by_its_manifest(self, folder):
        outcome = ingest_folder(folder, TODAY, "synthetic")
        assert outcome.errors == [] and outcome.rejected == 0 and outcome.accepted > 1000
        assert {label.split(" (")[0] for label, _ in outcome.results} >= {
            "academic facts", "research facts", "research publications", "placement facts", "finance facts"
        }  # fmt: skip

    def test_reading_the_same_folder_twice_adds_nothing(self, folder):
        first = ingest_folder(folder, TODAY, "synthetic")
        outcome = ingest_folder(folder, TODAY, "synthetic")  # a fresh ledger, but the same bytes
        assert outcome.accepted == first.accepted
        # and within one ledger a repeat is a no-op, shown on the report
        ledger = first.ledger
        from app.ingestion.adapters import CsvAdapter
        from app.ingestion.rows import FACT_REQUIRED

        source = ledger.sources[0]
        again = ledger.ingest_facts(
            CsvAdapter(folder / "academic.csv", required=FACT_REQUIRED),
            source,
            source_domain(source),
            "t",
        )
        assert again.noop

    def test_one_unreadable_file_is_reported_and_the_others_are_still_read(self, folder):
        (folder / "finance.csv").write_text("dept_code,value\nCSE,1\n")
        outcome = ingest_folder(folder, TODAY, "synthetic")
        assert (
            len(outcome.errors) == 1
            and "finance facts" in outcome.errors[0]
            and "metric_key" in outcome.errors[0]
        )
        assert any("academic" in label for label, _ in outcome.results)

    def test_a_listed_file_that_is_not_there_is_reported_not_a_crash(self, folder):
        (folder / "placement.csv").unlink()
        outcome = ingest_folder(folder, TODAY, "synthetic")
        assert any("placement facts" in e for e in outcome.errors)

    def test_a_source_in_the_manifest_can_rename_its_columns(self, folder):
        text = (folder / "academic.csv").read_text().replace("dept_code", "Department", 1)
        (folder / "academic.csv").write_text(text)
        edit_manifest(
            folder, lambda m: m["sources"][0].update(column_map={"dept_code": "Department"})
        )
        outcome = ingest_folder(folder, TODAY, "synthetic")
        assert outcome.errors == [] and outcome.rejected == 0

    def test_no_manifest_is_a_plain_error(self, tmp_path):
        with pytest.raises(ManifestError, match="no manifest.yml"):
            ingest_folder(tmp_path, TODAY)

    def test_a_source_with_an_unknown_area_is_refused(self, folder):
        edit_manifest(folder, lambda m: m["sources"][0].update(domain="astrology"))
        with pytest.raises(ManifestError, match="needs a domain"):
            ingest_folder(folder, TODAY)

    def test_a_department_listed_twice_is_refused(self, tmp_path):
        write_csv(
            tmp_path / "departments.csv",
            ("code", "name", "school"),
            [["CSE", "A", "S"], ["cse", "B", "S"]],
        )
        with pytest.raises(ManifestError, match="listed twice"):
            read_departments(tmp_path / "departments.csv")

    def test_a_department_with_no_name_is_refused(self, tmp_path):
        write_csv(tmp_path / "departments.csv", ("code", "name", "school"), [["CSE", "", "S"]])
        with pytest.raises(ManifestError, match="needs a code and a name"):
            read_departments(tmp_path / "departments.csv")


def source_domain(source):
    from app.domain.enums import Domain

    return Domain.ACADEMIC


class TestReconciliationReport:
    @pytest.fixture
    def report(self, folder):
        return reconciliation_report(
            ingest_folder(folder, TODAY, "synthetic"), "the synthetic sample"
        )

    def test_it_says_how_much_came_in_and_how_much_was_refused(self, report):
        assert "rows accepted, 0 rejected" in report and "## Files" in report

    def test_a_department_with_no_record_is_shown_as_none_never_as_zero(self, report):
        row = next(line for line in report.splitlines() if line.startswith("| MECH |"))
        assert "none" in row  # trap T2: no research record for the current year

    def test_a_stale_department_shows_how_old_its_newest_record_is(self, report):
        row = next(line for line in report.splitlines() if line.startswith("| CIVIL |"))
        assert "150 days" in row  # trap T1

    def test_records_that_are_not_final_are_listed_so_the_owner_can_confirm_them(self, report):
        section = report.split("## Records that are not final")[1].split("##")[0]
        assert (
            "provisional" in section
            and "forecast" in section
            and "pending reconciliation" in section
        )

    def test_rejected_rows_are_listed_with_where_and_why(self, folder):
        rows = [fact(), fact(status=""), fact(dept_code="XYZ", value="oops")]
        fact_file(folder, rows, "academic.csv")
        report = reconciliation_report(ingest_folder(folder, TODAY, "synthetic"), "x")
        assert "## Rejected rows (2)" in report
        assert "academic.csv:row 3 | the status is missing" in report
        assert "unknown department 'XYZ'" in report and "value 'oops' is not a number" in report

    def test_files_that_could_not_be_read_come_first(self, folder):
        (folder / "finance.csv").write_text("dept_code\n")
        assert (
            reconciliation_report(ingest_folder(folder, TODAY, "synthetic"), "x").index(
                "could not be read"
            )
            < 400
        )


class TestTemplates:
    """What a data owner is handed (`make seed` writes it to data/sample/templates)."""

    @pytest.fixture
    def templates(self, tmp_path) -> Path:
        from app.ingestion.export import export_templates

        export_templates(tmp_path / "templates")
        return tmp_path / "templates"

    def test_a_template_folder_is_refused_until_its_sources_are_named(self, templates):
        with pytest.raises(ManifestError, match="academic source still says 'CHANGE ME'"):
            ingest_folder(templates, TODAY, "real")

    def test_filled_in_as_its_example_rows_show_it_reads_cleanly(self, templates):
        def name_sources(manifest):
            for entry in manifest["sources"]:
                entry["name"] = f"{entry['domain']} register"
                entry["owner_office"] = "Registrar's Office"

        edit_manifest(templates, name_sources)
        outcome = ingest_folder(templates, TODAY, "real")
        assert outcome.errors == [] and outcome.rejected == 0
        assert outcome.accepted == 2  # the worked academic row and the example paper
        [paper] = outcome.ledger.publications
        assert paper.dept_codes == ("CSE", "ECE")
