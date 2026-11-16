"""What is allowed in, and the plain reason for everything that is not (docs/DATA_CONTRACT.md 7)."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.enums import Domain, FactStatus
from app.ingestion.rows import RawRow
from app.ingestion.validator import validate_facts, validate_publications

from .conftest import fact

TODAY = date(2026, 10, 1)
DEPTS = {"CSE", "ECE"}


def check(*rows, domain=Domain.ACADEMIC):
    raw = [
        RawRow(f"academic.csv:row {i + 2}", {k: (v or None) for k, v in r.items()})
        for i, r in enumerate(rows)
    ]
    return validate_facts(raw, domain, DEPTS, TODAY)


class TestAccepted:
    def test_a_good_row_is_accepted_and_keeps_where_it_came_from(self):
        accepted, rejects = check(fact())
        assert rejects == [] and len(accepted) == 1
        row = accepted[0]
        assert row.value == Decimal("4600") and row.status is FactStatus.FINAL
        assert row.unit == "students"  # from the catalogue, not left to the file
        assert row.source_ref == "academic.csv:row 2"

    def test_the_sources_own_reference_wins_when_it_has_one(self):
        (row,), _ = check(fact(source_ref="exam-system:result/881"))
        assert row.source_ref == "exam-system:result/881"

    @pytest.mark.parametrize("text", ["2026-09-09", "09/09/2026", "09-09-2026", "09.09.2026"])
    def test_dates_are_read_the_way_indian_offices_write_them(self, text):
        (row,), _ = check(fact(as_of=text))
        assert row.as_of == date(2026, 9, 9)

    def test_a_day_first_date_is_never_read_month_first(self):
        (row,), _ = check(fact(as_of="05/09/2026"))
        assert row.as_of == date(2026, 9, 5)

    def test_thousands_separators_are_read(self):
        (row,), _ = check(fact(value="1,250"))
        assert row.value == Decimal("1250")

    @pytest.mark.parametrize("text", ["Final", "FINAL", " final "])
    def test_a_status_is_read_whatever_its_case(self, text):
        (row,), _ = check(fact(status=text))
        assert row.status is FactStatus.FINAL

    def test_pending_reconciliation_can_be_written_with_spaces_or_hyphens(self):
        for text in ("Pending Reconciliation", "pending-reconciliation"):
            (row,), _ = check(fact(metric_key="acad.students_appeared", status=text))
            assert row.status is FactStatus.PENDING_RECONCILIATION

    def test_a_department_code_is_matched_whatever_its_case(self):
        (row,), _ = check(fact(dept_code="cse"))
        assert row.dept_code == "CSE"

    def test_a_numerator_and_denominator_travel_together(self):
        (row,), _ = check(fact(numerator="7940", denominator="9200"))
        assert (row.numerator, row.denominator) == (Decimal("7940"), Decimal("9200"))

    def test_a_zero_denominator_is_accepted_because_the_engine_calls_it_undefined_not_zero(self):
        (row,), rejects = check(fact(numerator="0", denominator="0"))
        assert rejects == [] and row.denominator == 0


REJECTED = [
    ({"status": ""}, "the status is missing"),
    ({"as_of": ""}, "the as-of date is missing"),
    ({"value": ""}, "the value is missing"),
    ({"dept_code": ""}, "the department is missing"),
    ({"metric_key": ""}, "the metric is missing"),
    ({"status": "approved"}, "status 'approved' is not one of"),
    ({"as_of": "yesterday"}, "is not a date"),
    ({"as_of": "2026-10-02"}, "in the future"),
    ({"dept_code": "XYZ"}, "unknown department 'XYZ'"),
    ({"metric_key": "acad.vibes"}, "unknown metric 'acad.vibes'"),
    ({"metric_key": "plc.placed_confirmed"}, "belongs to placement, but this source is academic"),
    ({"period_year": "2025"}, "should look like 2025-26"),
    ({"period_sub": "H1"}, "sub-period 'H1'"),
    ({"value": "lots"}, "value 'lots' is not a number"),
    ({"value": "NaN"}, "not a finite number"),
    ({"value": "-4"}, "is negative"),
    ({"numerator": "5"}, "a numerator needs a denominator"),
    ({"denominator": "5"}, "a numerator needs a denominator"),
    ({"numerator": "5", "denominator": "-1"}, "denominator is negative"),
    ({"unit": "crore"}, "does not match 'students'"),
]


@pytest.mark.parametrize(("change", "reason"), REJECTED)
def test_a_row_that_breaks_a_rule_is_rejected_with_the_reason(change, reason):
    accepted, rejects = check(fact(**change))
    assert accepted == []
    assert len(rejects) == 1 and reason in "; ".join(rejects[0].reasons)
    assert rejects[0].ref == "academic.csv:row 2"


def test_every_problem_in_a_row_is_reported_not_only_the_first():
    _, rejects = check(fact(status="", as_of="", dept_code="XYZ"))
    assert len(rejects[0].reasons) == 3


def test_good_rows_around_a_bad_one_are_still_accepted():
    accepted, rejects = check(fact(), fact(dept_code="XYZ"), fact(dept_code="ECE"))
    assert [r.dept_code for r in accepted] == ["CSE", "ECE"] and len(rejects) == 1
    assert rejects[0].ref == "academic.csv:row 3"


def test_a_repeated_slot_in_one_file_is_rejected_pointing_at_the_first():
    accepted, rejects = check(fact(), fact(value="9999"))
    assert len(accepted) == 1 and accepted[0].value == Decimal("4600")
    assert "duplicate of academic.csv:row 2" in rejects[0].reasons[0]


class TestTheRuleThatKeepsAForecastFromBeingTakenForFinal:
    def test_a_revenue_forecast_must_say_it_is_a_forecast(self):
        _, rejects = check(
            fact(metric_key="fin.revenue_forecast", status="final"), domain=Domain.FINANCE
        )
        assert "must have the status forecast" in rejects[0].reasons[0]
        accepted, _ = check(
            fact(metric_key="fin.revenue_forecast", status="forecast"), domain=Domain.FINANCE
        )
        assert accepted

    def test_actual_revenue_is_not_held_to_that_rule(self):
        accepted, rejects = check(
            fact(metric_key="fin.revenue_actual", status="final"), domain=Domain.FINANCE
        )
        assert accepted and not rejects

    @pytest.mark.parametrize("status", ["provisional", "final"])
    def test_a_count_of_provisional_offers_may_be_provisional_now_or_final_once_a_year_has_closed(
        self, status
    ):
        accepted, rejects = check(
            fact(metric_key="plc.offers_provisional", status=status), domain=Domain.PLACEMENT
        )
        assert accepted and not rejects


class TestPublications:
    def row(self, **over):
        values = {"dedup_key": "10.1000/ABC", "title": "A paper", "period_year": "2025-26", "status": "final",
                  "dept_codes": "CSE;ECE", "venue": "Journal", "indexing": "Scopus"}  # fmt: skip
        values.update(over)
        return RawRow("publications.csv:row 2", {k: (v or None) for k, v in values.items()})

    def test_a_good_publication_is_accepted_with_every_department_credited(self):
        (pub,), rejects = validate_publications([self.row()], DEPTS)
        assert rejects == [] and pub.dept_codes == ("CSE", "ECE")
        assert pub.dedup_key == "10.1000/abc"  # a DOI has no case, so two spellings are one paper

    @pytest.mark.parametrize("separator", [";", ",", " ; "])
    def test_departments_may_be_separated_by_semicolons_or_commas(self, separator):
        (pub,), _ = validate_publications([self.row(dept_codes=f"CSE{separator}ECE")], DEPTS)
        assert pub.dept_codes == ("CSE", "ECE")

    @pytest.mark.parametrize(
        ("change", "reason"),
        [
            ({"dedup_key": ""}, "cannot be counted once"),
            ({"title": ""}, "the title is missing"),
            ({"dept_codes": ""}, "no department is credited"),
            ({"dept_codes": "CSE;XYZ"}, "unknown department XYZ"),
            ({"status": ""}, "the status is missing"),
            ({"period_year": "25"}, "should look like"),
        ],
    )
    def test_a_publication_that_breaks_a_rule_is_rejected_with_the_reason(self, change, reason):
        accepted, rejects = validate_publications([self.row(**change)], DEPTS)
        assert accepted == [] and reason in rejects[0].reasons[0]
