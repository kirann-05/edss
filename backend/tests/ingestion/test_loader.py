"""The ledger: batches, no-ops, history that is kept, and one paper counted once."""

from datetime import date

import pytest

from app.domain.dataset import current_facts
from app.domain.enums import Domain, FactStatus
from app.ingestion.adapters import CsvAdapter
from app.ingestion.loader import Ledger
from app.ingestion.rows import FACT_REQUIRED, PUBLICATION_REQUIRED

from .conftest import DEPARTMENTS, TODAY, fact, fact_file, publication_file


@pytest.fixture
def ledger():
    return Ledger(DEPARTMENTS, TODAY, data_mode="synthetic")


def adapter(path):
    return CsvAdapter(path, required=FACT_REQUIRED)


def pub_adapter(path):
    return CsvAdapter(path, required=PUBLICATION_REQUIRED)


class TestFacts:
    def test_accepted_rows_become_facts_with_ids_a_batch_and_their_source(self, ledger, tmp_path):
        source = ledger.source("Exam Section", "Controller of Examinations", "csv")
        result = ledger.ingest_facts(
            adapter(fact_file(tmp_path, [fact(), fact(dept_code="ECE")])),
            source,
            Domain.ACADEMIC,
            "tester",
        )
        assert (result.accepted, len(result.rejects), result.noop) == (2, 0, False)
        assert [f.id for f in ledger.facts] == [1, 2]
        assert {f.batch_id for f in ledger.facts} == {result.batch.id} and ledger.facts[
            0
        ].source_system_id == source.id
        assert result.batch.row_count == 2 and result.batch.rejected_count == 0
        assert result.batch.ingested_by == "tester" and result.batch.data_mode == "synthetic"

    def test_rejected_rows_are_counted_and_reported_never_swallowed(self, ledger, tmp_path):
        source = ledger.source("s", "o", "csv")
        rows = [fact(), fact(status=""), fact(dept_code="XYZ")]
        result = ledger.ingest_facts(
            adapter(fact_file(tmp_path, rows)), source, Domain.ACADEMIC, "t"
        )
        assert result.accepted == 1 and len(result.rejects) == 2
        assert result.batch.rejected_count == 2 and len(ledger.facts) == 1
        assert [r.ref for r in result.rejects] == ["academic.csv:row 3", "academic.csv:row 4"]

    def test_the_same_content_ingested_again_is_a_no_op(self, ledger, tmp_path):
        source = ledger.source("s", "o", "csv")
        path = fact_file(tmp_path, [fact()])
        first = ledger.ingest_facts(adapter(path), source, Domain.ACADEMIC, "t")
        again = ledger.ingest_facts(adapter(path), source, Domain.ACADEMIC, "t")
        assert again.noop and again.batch == first.batch
        assert len(ledger.facts) == 1 and len(ledger.batches) == 1

    def test_the_same_content_from_another_source_is_not_a_repeat(self, ledger, tmp_path):
        path = fact_file(tmp_path, [fact()])
        ledger.ingest_facts(adapter(path), ledger.source("a", "o", "csv"), Domain.ACADEMIC, "t")
        other = ledger.ingest_facts(
            adapter(path), ledger.source("b", "o", "csv"), Domain.ACADEMIC, "t"
        )
        assert not other.noop and len(ledger.facts) == 2

    def test_a_changed_file_is_a_new_batch_and_the_newest_figure_is_the_current_one(
        self, ledger, tmp_path
    ):
        source = ledger.source("s", "o", "csv")
        ledger.ingest_facts(
            adapter(fact_file(tmp_path, [fact(value="4600")], "v1.csv")),
            source,
            Domain.ACADEMIC,
            "t",
        )
        ledger.ingest_facts(
            adapter(fact_file(tmp_path, [fact(value="4650")], "v2.csv")),
            source,
            Domain.ACADEMIC,
            "t",
        )
        assert len(ledger.facts) == 2 and len(ledger.batches) == 2
        (current,) = current_facts(ledger.facts)
        assert str(current.value) == "4650" and current.batch_id == 2

    def test_a_superseded_figure_is_kept_so_an_old_brief_can_still_cite_it(self, ledger, tmp_path):
        source = ledger.source("s", "o", "csv")
        ledger.ingest_facts(
            adapter(fact_file(tmp_path, [fact(value="4600")], "v1.csv")),
            source,
            Domain.ACADEMIC,
            "t",
        )
        ledger.ingest_facts(
            adapter(fact_file(tmp_path, [fact(value="4650")], "v2.csv")),
            source,
            Domain.ACADEMIC,
            "t",
        )
        dataset = ledger.dataset()
        assert {str(f.value) for f in dataset.facts} == {"4600", "4650"}  # both stay
        assert 1 in {f.id for f in dataset.facts}  # fact 1 still resolves

    def test_slots_the_newer_batch_does_not_cover_keep_their_older_figure(self, ledger, tmp_path):
        source = ledger.source("s", "o", "csv")
        ledger.ingest_facts(
            adapter(fact_file(tmp_path, [fact(), fact(dept_code="ECE", value="3000")], "v1.csv")),
            source,
            Domain.ACADEMIC,
            "t",
        )
        ledger.ingest_facts(
            adapter(fact_file(tmp_path, [fact(value="4650")], "v2.csv")),
            source,
            Domain.ACADEMIC,
            "t",
        )
        current = {f.dept_code: str(f.value) for f in current_facts(ledger.facts)}
        assert current == {"CSE": "4650", "ECE": "3000"}


class TestPublications:
    def row(self, **over):
        base = {"dedup_key": "10.1000/abc", "title": "A paper", "period_year": "2025-26", "status": "final",
                "dept_codes": "CSE", "venue": "J", "indexing": "Scopus"}  # fmt: skip
        base.update(over)
        return base

    def test_a_paper_listed_under_two_departments_is_one_paper_credited_to_both(
        self, ledger, tmp_path
    ):
        source = ledger.source("Research Office", "o", "csv")
        rows = [
            self.row(dept_codes="CSE"),
            self.row(dept_codes="ECE"),
            self.row(dedup_key="10.1000/zzz", title="Other"),
        ]
        result = ledger.ingest_publications(
            pub_adapter(publication_file(tmp_path, rows)), source, "t"
        )
        assert result.accepted == 3  # three rows came in
        assert len(ledger.publications) == 2  # two papers
        shared = next(p for p in ledger.publications if p.dedup_key == "10.1000/abc")
        assert shared.dept_codes == ("CSE", "ECE")

    def test_two_spellings_of_one_doi_are_one_paper(self, ledger, tmp_path):
        rows = [
            self.row(dedup_key="10.1000/ABC", dept_codes="CSE"),
            self.row(dedup_key="10.1000/abc", dept_codes="ECE"),
        ]
        ledger.ingest_publications(
            pub_adapter(publication_file(tmp_path, rows)), ledger.source("s", "o", "csv"), "t"
        )
        assert len(ledger.publications) == 1

    def test_a_paper_is_only_as_final_as_its_least_final_listing(self, ledger, tmp_path):
        rows = [
            self.row(dept_codes="CSE", status="final"),
            self.row(dept_codes="ECE", status="provisional"),
        ]
        ledger.ingest_publications(
            pub_adapter(publication_file(tmp_path, rows)), ledger.source("s", "o", "csv"), "t"
        )
        assert ledger.publications[0].status is FactStatus.PROVISIONAL

    def test_the_same_paper_in_two_years_is_two_records(self, ledger, tmp_path):
        rows = [self.row(period_year="2024-25"), self.row(period_year="2025-26")]
        ledger.ingest_publications(
            pub_adapter(publication_file(tmp_path, rows)), ledger.source("s", "o", "csv"), "t"
        )
        assert len(ledger.publications) == 2

    def test_a_publication_file_ingested_twice_is_a_no_op(self, ledger, tmp_path):
        source = ledger.source("s", "o", "csv")
        path = publication_file(tmp_path, [self.row()])
        ledger.ingest_publications(pub_adapter(path), source, "t")
        assert ledger.ingest_publications(pub_adapter(path), source, "t").noop
        assert len(ledger.publications) == 1


class TestTheDataset:
    def test_it_lists_the_periods_in_order_and_takes_the_newest_as_current(self, ledger, tmp_path):
        source = ledger.source("s", "o", "csv")
        rows = [
            fact(period_year="2025-26"),
            fact(period_year="2023-24", dept_code="ECE"),
            fact(period_year="2024-25", dept_code="ECE", period_sub="S2"),
        ]
        ledger.ingest_facts(adapter(fact_file(tmp_path, rows)), source, Domain.ACADEMIC, "t")
        dataset = ledger.dataset()
        assert (
            dataset.periods == ("2023-24", "2024-25", "2025-26")
            and dataset.current_period == "2025-26"
        )
        assert dataset.reference_date == date(2026, 10, 1) and dataset.departments == DEPARTMENTS

    def test_the_current_period_can_be_chosen(self, ledger, tmp_path):
        ledger.ingest_facts(
            adapter(fact_file(tmp_path, [fact(), fact(period_year="2024-25", dept_code="ECE")])),
            ledger.source("s", "o", "csv"),
            Domain.ACADEMIC,
            "t",
        )
        assert ledger.dataset(current_period="2024-25").current_period == "2024-25"

    def test_nothing_ingested_is_an_error_not_an_empty_report(self, ledger):
        with pytest.raises(ValueError, match="nothing has been ingested"):
            ledger.dataset()

    def test_a_source_is_registered_once_by_name(self, ledger):
        assert ledger.source("A", "o", "csv") is ledger.source("A", "o", "csv")
        assert ledger.source("B", "o", "csv").id == 2
