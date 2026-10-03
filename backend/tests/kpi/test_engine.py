from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domain.enums import Domain, FactStatus, KpiFramework, KpiStatus
from app.domain.models import Department, KpiDefinition, KpiTarget, MetricFact, Publication
from app.kpi.catalogue import CATALOGUE
from app.kpi.engine import PeriodData, compute_all, compute_kpi, judge
from app.kpi.results import DeptState

TODAY = date(2026, 10, 1)
PERIOD = "2025-26"
FRESH = TODAY - timedelta(days=10)
D = Decimal


def dept(code):
    return Department(code=code, name=f"Dept {code}", school="School")


def fact(fid, key, d, value, *, status=FactStatus.FINAL, sub="AY", as_of=FRESH, period=PERIOD):
    spec = CATALOGUE[key]
    return MetricFact(
        id=fid,
        batch_id=1,
        domain=spec.domain,
        metric_key=key,
        dept_code=d,
        period_year=period,
        period_sub=sub,
        value=D(str(value)),
        unit=spec.unit,
        status=status,
        as_of=as_of,
        source_system_id=1,
        source_ref=f"test:{fid}",
    )


def kpi(key, formula, *, higher=True, band="2", unit="%"):
    return KpiDefinition(
        key=key,
        name=key,
        framework=KpiFramework.STRATEGIC,
        domain=Domain.PLACEMENT,
        domain_tags=(Domain.PLACEMENT,),
        formula=formula,
        unit=unit,
        higher_is_better=higher,
        at_risk_band_pct=D(band),
    )


def target(key, value):
    return KpiTarget(
        kpi_key=key,
        period_year=PERIOD,
        target_value=D(str(value)),
        framework=KpiFramework.STRATEGIC,
        source_doc="test",
    )


def data(depts, facts, pubs=(), current=True):
    return PeriodData(
        period_year=PERIOD,
        departments=tuple(dept(c) for c in depts),
        facts=tuple(facts),
        publications=tuple(pubs),
        is_current=current,
    )


PL_PCT = kpi("PL_PCT", '100 * sum("plc.placed_confirmed") / sum("plc.registered")')


def compute(definition, tgt, period_data, stale_after_days=90):
    return compute_kpi(
        definition,
        target(definition.key, tgt) if tgt is not None else None,
        period_data,
        TODAY,
        stale_after_days,
    )


def placement(fid, d, registered, placed, **kw):
    return [
        fact(fid, "plc.registered", d, registered, **kw),
        fact(fid + 1, "plc.placed_confirmed", d, placed, **kw),
    ]


class TestRoundingAndStatus:
    def test_t6_a_miss_is_never_hidden_by_rounding(self):
        facts = placement(1, "A", 2500, 1874)
        result = compute(PL_PCT, 75, data(["A"], facts))
        assert result.value == D("74.96")
        assert result.status is KpiStatus.MISSED
        assert result.variance_abs == D("-0.04")

    def test_status_is_decided_on_the_unrounded_value(self):
        facts = placement(1, "A", 10**10, 7_499_999_999)  # 74.99999999 percent
        result = compute(PL_PCT, 75, data(["A"], facts))
        assert result.status is KpiStatus.MISSED

    @pytest.mark.parametrize(
        ("value", "tgt", "higher", "expected"),
        [
            ("71.2", "75", True, KpiStatus.MISSED),
            ("74.96", "75", True, KpiStatus.MISSED),
            ("75", "75", True, KpiStatus.AT_RISK),  # on target, no margin
            ("76.4", "75", True, KpiStatus.AT_RISK),  # margin 1.4 < 2% of 75 = 1.5
            ("76.5", "75", True, KpiStatus.MET),  # margin exactly the band
            ("90", "75", True, KpiStatus.MET),
            ("8", "10", False, KpiStatus.MET),  # lower is better, 20% under
            ("10", "10", False, KpiStatus.AT_RISK),
            ("10.01", "10", False, KpiStatus.MISSED),
        ],
    )
    def test_status_bands_respect_direction(self, value, tgt, higher, expected):
        status, _, _ = judge(D(value), D(tgt), higher, D("2"))
        assert status is expected

    def test_variance_is_signed_value_minus_target(self):
        _, variance_abs, variance_pct = judge(D("71.25"), D("75"), True, D("2"))
        assert variance_abs == D("-3.75")
        assert variance_pct == D("-5")

    def test_no_target_means_no_status_and_a_flag(self):
        facts = placement(1, "A", 100, 80)
        result = compute(PL_PCT, None, data(["A"], facts))
        assert result.value == D("80")
        assert result.status is KpiStatus.UNDEFINED
        assert result.flags.no_target is True
        assert result.variance_abs is None


class TestAggregation:
    def test_t7_institution_percentage_comes_from_totals(self):
        facts = placement(1, "BIG", 1000, 800) + placement(3, "SMALL", 50, 49)
        result = compute(PL_PCT, 75, data(["BIG", "SMALL"], facts))
        assert result.value == D("849") * 100 / D("1050")
        by_dept = {v.dept_code: v.value for v in result.departments}
        assert by_dept == {"BIG": D("80"), "SMALL": D("98")}
        assert result.value != (by_dept["BIG"] + by_dept["SMALL"]) / 2

    def test_sum_metrics_add_sub_periods_and_snapshots_take_the_latest(self):
        facts = [
            fact(1, "acad.students_passed", "A", 40, sub="S1"),
            fact(2, "acad.students_passed", "A", 50, sub="S2"),
            fact(3, "acad.students_appeared", "A", 50, sub="S1"),
            fact(4, "acad.students_appeared", "A", 50, sub="S2"),
            fact(5, "acad.courses_total", "A", 30, sub="S1"),
            fact(6, "acad.courses_total", "A", 34, sub="S2"),
            fact(7, "acad.courses_current_revision", "A", 20, sub="S1"),
            fact(8, "acad.courses_current_revision", "A", 17, sub="S2"),
        ]
        pass_pct = kpi(
            "AC_PASS_PCT", '100 * sum("acad.students_passed") / sum("acad.students_appeared")'
        )
        curr = kpi(
            "AC_CURR", '100 * sum("acad.courses_current_revision") / sum("acad.courses_total")'
        )
        pd = data(["A"], facts)
        assert compute(pass_pct, 80, pd).value == D("90")
        result = compute(curr, 80, pd)
        assert result.value == D("50")  # latest: 17 of 34
        assert set(result.input_fact_ids) == {6, 8}  # the superseded S1 snapshots are not inputs

    def test_every_result_lists_the_facts_it_used(self):
        facts = placement(1, "A", 100, 80) + placement(3, "B", 100, 60)
        result = compute(PL_PCT, 75, data(["A", "B"], facts))
        assert result.input_fact_ids == (1, 2, 3, 4)
        assert {t.label for t in result.inputs} == {
            "sum(plc.placed_confirmed)",
            "sum(plc.registered)",
        }

    def test_department_values_use_the_same_formula_over_one_department(self):
        facts = placement(1, "A", 100, 80) + placement(3, "B", 100, 60)
        result = compute(PL_PCT, 75, data(["A", "B"], facts))
        a = next(v for v in result.departments if v.dept_code == "A")
        assert a.state is DeptState.OK
        assert a.value == D("80")
        assert a.input_fact_ids == (1, 2)
        assert {t.label: t.value for t in a.inputs}["sum(plc.registered)"] == D("100")


class TestTraps:
    def test_t9_zero_denominator_department_is_undefined_and_does_not_distort_the_total(self):
        facts = placement(1, "A", 20, 10) + placement(3, "NEW", 0, 0)
        result = compute(PL_PCT, 75, data(["A", "NEW"], facts))
        new = next(v for v in result.departments if v.dept_code == "NEW")
        assert new.state is DeptState.UNDEFINED
        assert new.value is None
        assert result.value == D("50")
        assert result.flags.undefined_departments == ("NEW",)

    def test_when_every_denominator_is_zero_the_institution_value_is_undefined(self):
        facts = placement(1, "A", 0, 0)
        result = compute(PL_PCT, 75, data(["A"], facts))
        assert result.value is None
        assert result.status is KpiStatus.UNDEFINED

    def test_t2_a_department_with_no_data_is_missing_not_zero(self):
        rs = kpi("RS_PUB_PF", 'unique_publications() / sum("ref.faculty_count")', unit="ratio")
        facts = [
            fact(1, "res.publications_count", "A", 2),
            fact(2, "ref.faculty_count", "A", 10),
            fact(3, "ref.faculty_count", "B", 90),  # B has faculty but no research record
        ]
        pubs = [
            Publication(
                id=1,
                batch_id=1,
                dedup_key="p1",
                title="t",
                venue="v",
                period_year=PERIOD,
                indexing="scopus",
                status=FactStatus.FINAL,
                dept_codes=("A",),
            ),
            Publication(
                id=2,
                batch_id=1,
                dedup_key="p2",
                title="t",
                venue="v",
                period_year=PERIOD,
                indexing="scopus",
                status=FactStatus.FINAL,
                dept_codes=("A",),
            ),
        ]
        result = compute(rs, 1, data(["A", "B"], facts, pubs))
        b = next(v for v in result.departments if v.dept_code == "B")
        assert b.state is DeptState.MISSING
        assert b.value is None
        assert result.flags.missing_departments == ("B",)
        assert result.value == D(
            "0.2"
        )  # 2 publications over A's 10 faculty, B's 90 not diluting it

    def test_t5_a_shared_paper_counts_once_for_the_institution(self):
        rs = kpi("RS_PUB_PF", 'unique_publications() / sum("ref.faculty_count")', unit="ratio")
        facts = [
            fact(1, "res.publications_count", "A", 2),
            fact(2, "res.publications_count", "B", 2),
            fact(3, "ref.faculty_count", "A", 10),
            fact(4, "ref.faculty_count", "B", 10),
        ]

        def pub(pid, key, depts):
            return Publication(
                id=pid,
                batch_id=1,
                dedup_key=key,
                title="t",
                venue="v",
                period_year=PERIOD,
                indexing="scopus",
                status=FactStatus.FINAL,
                dept_codes=depts,
            )

        pubs = [
            pub(1, "doi:solo-a", ("A",)),
            pub(2, "doi:shared", ("A", "B")),
            pub(3, "doi:solo-b", ("B",)),
        ]
        result = compute(rs, 1, data(["A", "B"], facts, pubs))
        assert result.value == D("0.15")  # 3 unique papers over 20 faculty, not 4
        by_dept = {v.dept_code: v.value for v in result.departments}
        assert by_dept == {"A": D("0.2"), "B": D("0.2")}  # both departments keep their credit

    def test_t8_a_figure_pending_reconciliation_keeps_its_department_out_of_actuals(self):
        util = kpi("FN_UTIL", '100 * sum("fin.expenditure_actual") / sum("fin.budget_sanctioned")')
        facts = [
            fact(1, "fin.budget_sanctioned", "A", 100, sub="FY"),
            fact(2, "fin.expenditure_actual", "A", 60, sub="Q1"),
            fact(3, "fin.budget_sanctioned", "B", 100, sub="FY"),
            fact(4, "fin.expenditure_actual", "B", 30, sub="Q1"),
            fact(
                5,
                "fin.expenditure_actual",
                "B",
                40,
                sub="Q2",
                status=FactStatus.PENDING_RECONCILIATION,
            ),
        ]
        result = compute(util, 50, data(["A", "B"], facts))
        b = next(v for v in result.departments if v.dept_code == "B")
        assert b.state is DeptState.EXCLUDED
        assert result.flags.excluded_departments == ("B",)
        assert result.flags.excluded_fact_ids == (5,)
        assert result.value == D("60")  # A only
        assert 5 not in result.input_fact_ids
        assert 4 not in result.input_fact_ids  # B's other figures are not used either

    @pytest.mark.parametrize("status", [FactStatus.PROVISIONAL, FactStatus.FORECAST])
    def test_provisional_and_forecast_figures_never_count_as_actuals(self, status):
        rev = kpi("FN_REV", 'sum("fin.revenue_actual")', unit="INR lakh")
        facts = [
            fact(1, "fin.revenue_actual", "A", 100, sub="Q1"),
            fact(2, "fin.revenue_actual", "A", 50, sub="Q2", status=status),
            fact(3, "fin.revenue_actual", "B", 70, sub="Q1"),
        ]
        result = compute(rev, 100, data(["A", "B"], facts))
        assert result.value == D("70")
        assert result.flags.excluded_departments == ("A",)

    def test_a_forecast_metric_is_not_an_input_to_actual_revenue(self):
        rev = kpi("FN_REV", 'sum("fin.revenue_actual")', unit="INR lakh")
        facts = [
            fact(1, "fin.revenue_actual", "A", 100, sub="Q1"),
            fact(2, "fin.revenue_forecast", "A", 999, sub="Q4", status=FactStatus.FORECAST),
        ]
        result = compute(rev, 100, data(["A"], facts))
        assert result.value == D("100")
        assert result.input_fact_ids == (1,)

    def test_t1_stale_data_is_flagged_but_still_used(self):
        old = TODAY - timedelta(days=150)
        facts = placement(1, "FRESH", 100, 80) + placement(3, "OLD", 100, 60, as_of=old)
        result = compute(PL_PCT, 75, data(["FRESH", "OLD"], facts))
        assert result.flags.stale_departments == ("OLD",)
        assert result.value == D("70")  # OLD's figures still count
        assert result.as_of == old  # the result is only as fresh as its oldest input

    def test_staleness_is_judged_for_the_current_period_only(self):
        old = TODAY - timedelta(days=400)
        facts = placement(1, "A", 100, 80, as_of=old)
        result = compute(PL_PCT, 75, data(["A"], facts, current=False))
        assert result.flags.stale_departments == ()

    def test_stale_threshold_is_configurable(self):
        facts = placement(1, "A", 100, 80, as_of=TODAY - timedelta(days=30))
        assert compute(
            PL_PCT, 75, data(["A"], facts), stale_after_days=20
        ).flags.stale_departments == ("A",)
        assert (
            compute(PL_PCT, 75, data(["A"], facts), stale_after_days=90).flags.stale_departments
            == ()
        )


def test_compute_all_skips_inactive_definitions_and_keeps_order():
    facts = placement(1, "A", 100, 80)
    active = PL_PCT
    inactive = kpi("OLD", 'sum("plc.registered")').model_copy(update={"active": False})
    results = compute_all(
        [active, inactive], {"PL_PCT": target("PL_PCT", 75)}, data(["A"], facts), TODAY, 90
    )
    assert [r.kpi_key for r in results] == ["PL_PCT"]


def test_two_facts_for_one_slot_are_refused_rather_than_double_counted():
    from app.kpi.engine import DuplicateFactError

    facts = placement(1, "A", 100, 80) + [fact(9, "plc.registered", "A", 100)]
    with pytest.raises(DuplicateFactError, match="plc.registered"):
        compute(PL_PCT, 75, data(["A"], facts))
