"""One test per planted trap (docs/DATA_CONTRACT.md section 6).

Each asserts both that the trap is really in the data and that the system handles it.
"""

from decimal import Decimal

from app.domain.enums import FactStatus, KpiStatus
from app.kpi.results import DeptState
from app.synthetic.generator import SHARED_DOI

D = Decimal


def dept(result, code):
    return next(v for v in result.departments if v.dept_code == code)


def test_t1_one_departments_placement_data_is_stale_and_flagged(dataset, results, ref):
    placement = [
        f for f in dataset.facts if f.period_year == "2025-26" and f.metric_key.startswith("plc.")
    ]
    old = {f.dept_code for f in placement if (ref - f.as_of).days > 120}
    assert old == {"CIVIL"}
    assert (ref - next(f for f in placement if f.dept_code == "CIVIL").as_of).days == 150
    for key in ("PL_PCT", "PL_AVG", "PL_INT"):
        assert results[key].flags.stale_departments == ("CIVIL",)
        assert dept(results[key], "CIVIL").state is DeptState.OK  # still used, only flagged


def test_t2_one_department_has_no_research_record_for_the_latest_year(dataset, results):
    latest = [f for f in dataset.facts if f.period_year == "2025-26" and f.dept_code == "MECH"]
    assert not any(f.metric_key.startswith("res.") for f in latest)
    assert any(
        f.metric_key.startswith("res.")
        for f in dataset.facts
        if f.dept_code == "MECH" and f.period_year == "2024-25"
    )  # earlier years exist
    assert not [
        p for p in dataset.publications if p.period_year == "2025-26" and "MECH" in p.dept_codes
    ]
    for key in ("RS_PUB_PF", "RS_CIT_PP", "RS_GRANT_PF"):
        assert results[key].flags.missing_departments == ("MECH",)
        assert dept(results[key], "MECH").value is None  # missing is not zero


def test_t3_about_twelve_percent_of_offers_are_provisional_and_never_counted(
    dataset, results, facts_by_id
):
    current = [f for f in dataset.facts if f.period_year == "2025-26"]
    confirmed = sum(f.value for f in current if f.metric_key == "plc.placed_confirmed")
    provisional_facts = [f for f in current if f.metric_key == "plc.offers_provisional"]
    provisional = sum(f.value for f in provisional_facts)
    share = provisional / (confirmed + provisional)
    assert D("0.11") <= share <= D("0.13")
    assert any(f.status is FactStatus.PROVISIONAL and f.value > 0 for f in provisional_facts)
    used = {facts_by_id[i].metric_key for i in results["PL_PCT"].input_fact_ids}
    assert used == {"plc.placed_confirmed", "plc.registered"}


def test_t4_the_open_finance_quarter_has_a_forecast_that_is_never_summed_into_actuals(
    dataset, results, facts_by_id
):
    forecast = [f for f in dataset.facts if f.metric_key == "fin.revenue_forecast"]
    assert {f.period_sub for f in forecast} == {"Q4"}
    assert {f.period_year for f in forecast} == {"2025-26"}
    assert all(f.status is FactStatus.FORECAST for f in forecast)
    actual = sum(
        f.value
        for f in dataset.facts
        if f.metric_key == "fin.revenue_actual" and f.period_year == "2025-26"
    )
    assert results["FN_REV"].value == actual
    assert not {facts_by_id[i].metric_key for i in results["FN_REV"].input_fact_ids} & {
        "fin.revenue_forecast"
    }


def test_t5_two_departments_share_one_doi_counted_once_for_the_institution(dataset, results):
    shared = [p for p in dataset.publications if p.dedup_key == SHARED_DOI]
    assert len(shared) == 1
    assert set(shared[0].dept_codes) == {"CSE", "ECE"}
    current = [p for p in dataset.publications if p.period_year == "2025-26"]
    credits = sum(len(p.dept_codes) for p in current)
    unique = len({p.dedup_key for p in current})
    assert unique < credits
    # the institution figure uses unique papers over the faculty of departments with a record
    faculty = sum(
        f.value
        for f in dataset.facts
        if f.period_year == "2025-26"
        and f.metric_key == "ref.faculty_count"
        and f.dept_code != "MECH"
    )
    assert results["RS_PUB_PF"].value == D(unique) / faculty


def test_publication_credit_facts_agree_with_the_publication_rows(dataset):
    for period in dataset.periods:
        for code in {d.code for d in dataset.departments}:
            facts = [
                f
                for f in dataset.facts
                if f.period_year == period
                and f.dept_code == code
                and f.metric_key == "res.publications_count"
            ]
            credited = [
                p for p in dataset.publications if p.period_year == period and code in p.dept_codes
            ]
            assert sum(f.value for f in facts) == len(credited), (period, code)


def test_t6_a_kpi_computes_to_exactly_74_96_against_a_target_of_75(results):
    placement = results["PL_PCT"]
    assert placement.value == D("74.96")
    assert placement.target == D("75")
    assert placement.status is KpiStatus.MISSED
    assert placement.value.quantize(D("0.1")) == D("75.0")  # it would display as met
    assert placement.variance_abs == D("-0.04")


def test_t7_department_pass_rates_average_higher_than_the_weighted_institution_rate(results):
    passing = results["AC_PASS_PCT"]
    rates = [v.value for v in passing.departments]
    naive = sum(rates) / len(rates)
    assert abs(naive - passing.value) > D("2")
    inputs = {t.label: t.value for t in passing.inputs}
    assert (
        passing.value
        == 100 * inputs["sum(acad.students_passed)"] / inputs["sum(acad.students_appeared)"]
    )


def test_t8_one_finance_figure_is_pending_reconciliation_and_kept_out_of_actuals(dataset, results):
    pending = [f for f in dataset.facts if f.status is FactStatus.PENDING_RECONCILIATION]
    assert len(pending) == 1
    assert (pending[0].dept_code, pending[0].metric_key, pending[0].period_sub) == (
        "BIOTECH",
        "fin.expenditure_actual",
        "Q3",
    )
    util = results["FN_UTIL"]
    assert dept(util, "BIOTECH").state is DeptState.EXCLUDED
    assert util.flags.excluded_fact_ids == (pending[0].id,)
    assert pending[0].id not in util.input_fact_ids


def test_t9_a_department_with_a_zero_denominator_is_undefined_not_zero_or_hundred(results):
    for key in ("PL_PCT", "PL_AVG", "PL_INT"):
        aiml = dept(results[key], "AIML")
        assert aiml.state is DeptState.UNDEFINED
        assert aiml.value is None
        assert results[key].flags.undefined_departments == ("AIML",)
    assert results["PL_PCT"].value == D(937) / D(1250) * 100  # AIML does not distort the total


def test_t10_two_kpis_miss_one_is_at_risk_and_the_rest_are_met(results):
    by_status = {
        status: sorted(k for k, r in results.items() if r.status is status) for status in KpiStatus
    }
    assert by_status[KpiStatus.MISSED] == ["PL_PCT", "RS_PUB_PF"]
    assert by_status[KpiStatus.AT_RISK] == ["AC_PASS_PCT"]
    assert by_status[KpiStatus.UNDEFINED] == []
    assert len(by_status[KpiStatus.MET]) == 10


def test_every_kpi_result_lists_input_facts_that_exist_in_scope_and_are_actuals(
    results, facts_by_id
):
    for key, result in results.items():
        assert result.input_fact_ids, key
        for fact_id in result.input_fact_ids:
            fact = facts_by_id[fact_id]
            assert fact.period_year == "2025-26"
            assert fact.status in (FactStatus.FINAL, FactStatus.AUDITED), (key, fact_id)
        # a result is only as fresh as its oldest input
        assert result.as_of == min(facts_by_id[i].as_of for i in result.input_fact_ids)
