from decimal import Decimal

import pytest

from app.agents.compose import (
    build_assumptions,
    compose_brief,
    off_target,
    trend_word,
)
from app.agents.tokens import lint_numbers, render_text
from app.domain.enums import Domain, KpiStatus

D = Decimal


class TestTrendWord:
    @pytest.mark.parametrize(
        ("value", "previous", "higher", "expected"),
        [
            ("75", "70", True, "improving"),
            ("70", "75", True, "declining"),
            ("75.1", "75.0", True, "flat"),  # inside half a percent of the target
            ("65", "70", False, "improving"),  # lower is better
            ("75", "70", False, "declining"),
        ],
    )
    def test_direction_is_decided_in_code_from_the_figures(self, value, previous, higher, expected):
        assert trend_word(D(value), D(previous), D("75"), higher) == expected

    def test_without_two_periods_the_trend_is_unknown(self):
        assert trend_word(D("75"), None, D("75"), True) == "unknown"
        assert trend_word(None, D("70"), D("75"), True) == "unknown"


class TestFigures:
    def test_a_figure_remembers_which_departments_its_value_rests_on(self, figures):
        by_key = {f.key: f for f in figures}
        pub = by_key["RS_PUB_PF"]
        assert "MECH" not in pub.included_departments  # no record, so not in the value (T2)
        assert "CSE" in pub.included_departments
        placement = by_key["PL_PCT"]
        assert "AIML" in placement.included_departments  # in the figure, but undefined (T9)

    def test_a_figure_is_a_frozen_copy_with_its_sources(self, figures):
        for f in figures:
            assert f.input_fact_ids
            assert f.band_pct == D("2")
            assert f.trend in {"improving", "declining", "flat", "unknown"}

    def test_off_target_means_missed_or_at_risk(self, figures):
        assert {f.key for f in off_target(figures)} == {"PL_PCT", "RS_PUB_PF", "AC_PASS_PCT"}

    def test_every_status_gets_options_when_the_plan_asks_for_all(self, figures):
        assert len(off_target(figures, "all")) == len(figures)


class TestBrief:
    @pytest.fixture
    def brief(self, plan, figures, health):
        return compose_brief(plan, figures, (), health)

    def test_the_brief_covers_every_kpi_in_the_plan(self, brief, plan):
        assert {k.key for k in brief.kpis} == set(plan.kpi_keys)
        assert [s.kpi_key for s in brief.summary] == [k.key for k in brief.kpis]

    def test_a_headline_is_made_of_tokens_and_reads_back_exactly(self, brief, render_context):
        headline = next(s for s in brief.summary if s.kpi_key == "PL_PCT").headline
        assert lint_numbers(headline) == []  # no figure written by hand
        assert render_text(headline, render_context) == (
            "75.0% against a target of 75.0%: Missed, 0.04 pts below target."
        )

    def test_assumptions_say_what_the_reader_must_know(self, brief):
        by_kind = {}
        for item in brief.assumptions:
            by_kind.setdefault(item.kind, []).append(item)
        assert {"as_of", "placeholder", "stale", "missing", "excluded", "undefined"} <= set(by_kind)
        assert {i.dept_code for i in by_kind["stale"]} == {"CIVIL"}
        assert {i.dept_code for i in by_kind["missing"]} == {"MECH"}
        assert {i.dept_code for i in by_kind["excluded"]} == {"BIOTECH"}
        assert {i.dept_code for i in by_kind["undefined"]} == {"AIML"}
        assert "provisional" in by_kind and "forecast" in by_kind

    def test_every_assumption_is_free_of_hand_written_figures(self, brief):
        for item in brief.assumptions:
            assert lint_numbers(item.text) == [], item.text

    def test_the_data_health_section_names_every_stale_missing_or_non_final_cell(self, brief):
        notes = {(n.dept_code, n.domain.value): n for n in brief.data_health}
        assert notes[("CIVIL", "placement")].state == "stale"
        assert notes[("MECH", "research")].state == "missing"
        assert notes[("BIOTECH", "finance")].non_final
        assert ("CSE", "academic") not in notes  # a fresh, final cell needs no note

    def test_a_domain_left_out_of_the_plan_is_left_out_of_the_assumptions(
        self, plan, figures, health
    ):
        only_academic = [f for f in figures if f.domain is Domain.ACADEMIC]
        items = build_assumptions(only_academic, health, (Domain.ACADEMIC, Domain.REFERENCE))
        assert not any(i.kind in ("stale", "missing", "excluded") for i in items)
        assert not any(i.kind in ("provisional", "forecast") for i in items)

    def test_the_kpis_that_need_options_are_the_off_target_ones(self, brief):
        assert {k.key for k in brief.kpis if k.status is not KpiStatus.MET} >= {"PL_PCT"}
