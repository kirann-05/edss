"""The validation gate (docs/SPEC.md section 7): nine deterministic checks with locators.

The last class injects the eight faults from docs/ARCHITECTURE.md section 10 and asserts that
each is caught by the check that is meant to catch it. A clean brief must pass all nine.
"""

from decimal import Decimal

import pytest

from app.agents.compose import compose_brief, off_target
from app.agents.models import OptionSet
from app.agents.skills.options_skill import draft_option_set
from app.agents.validation.faults import CAUGHT_BY, FAULTS, apply_fault
from app.agents.validation.suite import ValidationContext, validate
from app.domain.enums import KpiStatus

D = Decimal


@pytest.fixture(scope="module")
def context(store, connector, plan):
    period = store.current_period
    return ValidationContext(
        plan=plan,
        facts=store.facts_by_id,
        sources=store.sources,
        publications=tuple(connector.get_publications(period)),
        definitions={d.key: d for d in store.definitions},
        approval_present=False,
    )


@pytest.fixture(scope="module")
def clean(plan, figures, health):
    from app.agents.llm import FakeLLM

    model = FakeLLM("drafter")
    sets = [draft_option_set(model, f) for f in off_target(figures)]
    return compose_brief(plan, figures, sets, health)


def failing_ids(report):
    return {c.id for c in report.checks if not c.passed}


class TestCleanBrief:
    def test_a_clean_brief_passes_every_check(self, clean, context):
        report = validate(clean, context)
        assert report.passed, [(c.id, [v.message for v in c.violations]) for c in report.failing]
        assert [c.id for c in report.checks] == [f"V{n}" for n in range(1, 10)]

    def test_each_check_carries_the_name_the_spec_gives_it(self, clean, context):
        names = {c.id: c.name for c in validate(clean, context).checks}
        assert names["V1"] == "Every figure cites its source"
        assert names["V5"] == "No action without approval"
        assert names["V9"] == "No double counting"


class TestV1Figures:
    def test_a_hand_written_figure_is_caught_with_its_option_as_the_locator(self, clean, context):
        faulty = apply_fault(clean, "fake_number", context)
        report = validate(faulty, context)
        v1 = next(c for c in report.checks if c.id == "V1")
        assert not v1.passed
        violation = v1.violations[0]
        assert violation.locator.kpi_key and violation.locator.option_id
        assert "12" in violation.diagnosis  # the diagnosis quotes what it found

    def test_a_token_that_resolves_to_nothing_is_caught(self, clean, context):
        first = clean.option_sets[0]
        bad = first.options[0].model_copy(
            update={"description": "See {{kpi:NO_SUCH_KPI}} for detail."}
        )
        faulty = clean.model_copy(
            update={
                "option_sets": (
                    OptionSet(kpi_key=first.kpi_key, options=(bad, *first.options[1:])),
                    *clean.option_sets[1:],
                )
            }
        )
        v1 = next(c for c in validate(faulty, context).checks if c.id == "V1")
        assert any("NO_SUCH_KPI" in v.message for v in v1.violations)


class TestV2Assumptions:
    def test_an_option_without_assumptions_fails(self, clean, context):
        first = clean.option_sets[0]
        bare = first.options[0].model_copy(update={"assumptions": ()})
        faulty = clean.model_copy(
            update={
                "option_sets": (
                    OptionSet(kpi_key=first.kpi_key, options=(bare, *first.options[1:])),
                    *clean.option_sets[1:],
                )
            }
        )
        v2 = next(c for c in validate(faulty, context).checks if c.id == "V2")
        assert not v2.passed and v2.violations[0].locator.option_id == bare.id

    def test_a_missing_as_of_statement_fails(self, clean, context):
        faulty = clean.model_copy(
            update={"assumptions": tuple(a for a in clean.assumptions if a.kind != "as_of")}
        )
        v2 = next(c for c in validate(faulty, context).checks if c.id == "V2")
        assert not v2.passed
        assert v2.violations[0].locator.section == "assumptions"


class TestV3RisksAndTradeOffs:
    def test_an_option_without_risks_fails(self, clean, context):
        report = validate(apply_fault(clean, "missing_risks", context), context)
        v3 = next(c for c in report.checks if c.id == "V3")
        assert not v3.passed and v3.violations[0].locator.option_id

    def test_an_option_without_trade_offs_fails(self, clean, context):
        first = clean.option_sets[0]
        bare = first.options[0].model_copy(update={"trade_offs": ()})
        faulty = clean.model_copy(
            update={
                "option_sets": (
                    OptionSet(kpi_key=first.kpi_key, options=(bare, *first.options[1:])),
                    *clean.option_sets[1:],
                )
            }
        )
        assert "V3" in failing_ids(validate(faulty, context))

    def test_a_blank_entry_does_not_count_as_a_risk(self, clean, context):
        first = clean.option_sets[0]
        blank = first.options[0].model_copy(update={"risks": ("   ",)})
        faulty = clean.model_copy(
            update={
                "option_sets": (
                    OptionSet(kpi_key=first.kpi_key, options=(blank, *first.options[1:])),
                    *clean.option_sets[1:],
                )
            }
        )
        assert "V3" in failing_ids(validate(faulty, context))


class TestV4NonFinalFigures:
    def test_a_provisional_figure_described_as_confirmed_is_caught(self, clean, context):
        report = validate(apply_fault(clean, "provisional_as_final", context), context)
        v4 = next(c for c in report.checks if c.id == "V4")
        assert not v4.passed
        assert "confirmed" in v4.violations[0].diagnosis

    def test_a_non_final_figure_must_be_called_what_it_is(self, clean, context, store):
        from app.domain.enums import FactStatus

        fact = next(f for f in store.facts_by_id.values() if f.status is FactStatus.PROVISIONAL)
        first = clean.option_sets[0]
        mention = first.options[0].model_copy(
            update={"description": f"Note {{{{fact:{fact.id}}}}} in this context."}
        )
        faulty = clean.model_copy(
            update={
                "option_sets": (
                    OptionSet(kpi_key=first.kpi_key, options=(mention, *first.options[1:])),
                    *clean.option_sets[1:],
                )
            }
        )
        v4 = next(c for c in validate(faulty, context).checks if c.id == "V4")
        assert not v4.passed  # it never says the figure is provisional

    def test_a_final_figure_needs_no_special_wording(self, clean, context, store):
        from app.domain.enums import FactStatus

        fact = next(f for f in store.facts_by_id.values() if f.status is FactStatus.FINAL)
        first = clean.option_sets[0]
        mention = first.options[0].model_copy(
            update={"description": f"Based on {{{{fact:{fact.id}}}}} as final."}
        )
        faulty = clean.model_copy(
            update={
                "option_sets": (
                    OptionSet(kpi_key=first.kpi_key, options=(mention, *first.options[1:])),
                    *clean.option_sets[1:],
                )
            }
        )
        assert "V4" not in failing_ids(validate(faulty, context))


class TestV5Approval:
    def test_a_document_that_claims_approval_without_a_record_fails(self, clean, context):
        report = validate(apply_fault(clean, "approval_bypass", context), context)
        v5 = next(c for c in report.checks if c.id == "V5")
        assert not v5.passed and v5.violations[0].locator.section == "status"

    def test_the_same_claim_passes_when_an_approval_record_exists(self, clean, context):
        approved = clean.model_copy(update={"claims_status": "approved"})
        with_record = ValidationContext(**{**context.__dict__, "approval_present": True})
        assert "V5" not in failing_ids(validate(approved, with_record))


class TestV6Definitions:
    def test_a_status_decided_on_a_rounded_value_is_caught(self, clean, context):
        report = validate(apply_fault(clean, "rounded_miss", context), context)
        v6 = next(c for c in report.checks if c.id == "V6")
        assert not v6.passed
        assert v6.violations[0].locator.kpi_key == "PL_PCT"
        assert "unrounded" in v6.violations[0].diagnosis

    def test_an_inactive_definition_fails(self, clean, context):
        retired = [
            f.model_copy(update={"definition_active": False}) if f.key == "AC_CO" else f
            for f in clean.kpis
        ]
        v6 = next(
            c
            for c in validate(clean.model_copy(update={"kpis": tuple(retired)}), context).checks
            if c.id == "V6"
        )
        assert not v6.passed and v6.violations[0].locator.kpi_key == "AC_CO"

    def test_a_non_placeholder_definition_must_be_approved(self, clean, context):
        unapproved = [
            f.model_copy(update={"placeholder": False, "definition_approved": False})
            if f.key == "AC_CO"
            else f
            for f in clean.kpis
        ]
        v6 = next(
            c
            for c in validate(clean.model_copy(update={"kpis": tuple(unapproved)}), context).checks
            if c.id == "V6"
        )
        assert not v6.passed

    def test_a_figure_from_an_older_definition_version_fails(self, clean, context):
        stale = [
            f.model_copy(update={"kpi_version": 0}) if f.key == "AC_CO" else f for f in clean.kpis
        ]
        assert "V6" in failing_ids(
            validate(clean.model_copy(update={"kpis": tuple(stale)}), context)
        )


class TestV7Traceability:
    def test_a_figure_with_no_source_records_is_caught(self, clean, context):
        report = validate(apply_fault(clean, "dropped_source", context), context)
        v7 = next(c for c in report.checks if c.id == "V7")
        assert not v7.passed and v7.violations[0].locator.kpi_key

    def test_a_source_record_that_does_not_exist_is_caught(self, clean, context):
        bad = [
            f.model_copy(update={"input_fact_ids": (999_999,)}) if f.key == "AC_CO" else f
            for f in clean.kpis
        ]
        v7 = next(
            c
            for c in validate(clean.model_copy(update={"kpis": tuple(bad)}), context).checks
            if c.id == "V7"
        )
        assert not v7.passed


class TestV8Coverage:
    def test_a_kpi_in_the_plan_but_not_the_brief_is_caught(self, clean, context):
        kept = tuple(f for f in clean.kpis if f.key != "AC_CO")
        summary = tuple(s for s in clean.summary if s.kpi_key != "AC_CO")
        v8 = next(
            c
            for c in validate(
                clean.model_copy(update={"kpis": kept, "summary": summary}), context
            ).checks
            if c.id == "V8"
        )
        assert not v8.passed and v8.violations[0].locator.kpi_key == "AC_CO"

    def test_an_off_target_kpi_with_no_options_is_caught(self, clean, context):
        faulty = clean.model_copy(update={"option_sets": clean.option_sets[1:]})
        v8 = next(c for c in validate(faulty, context).checks if c.id == "V8")
        assert not v8.passed
        assert v8.violations[0].locator.kpi_key == clean.option_sets[0].kpi_key

    def test_a_hidden_stale_department_is_caught(self, clean, context):
        report = validate(apply_fault(clean, "stale_hidden", context), context)
        assert {"V2", "V8"} <= failing_ids(report)

    def test_too_many_options_are_caught(self, clean, context):
        first = clean.option_sets[0]
        copies = tuple(first.options[0].model_copy(update={"id": f"X-{n}"}) for n in range(4))
        faulty = clean.model_copy(
            update={
                "option_sets": (
                    OptionSet(kpi_key=first.kpi_key, options=copies),
                    *clean.option_sets[1:],
                )
            }
        )
        v8 = next(c for c in validate(faulty, context).checks if c.id == "V8")
        assert not v8.passed
        assert "needs 2 or 3" in v8.violations[0].message


class TestV9DoubleCounting:
    def test_a_shared_paper_counted_twice_is_caught(self, clean, context):
        report = validate(apply_fault(clean, "double_count", context), context)
        v9 = next(c for c in report.checks if c.id == "V9")
        assert not v9.passed and v9.violations[0].locator.kpi_key == "RS_PUB_PF"


class TestFailureInjection:
    """CHECKLIST C7: every injected fault is detected by the check meant to catch it."""

    DETECTED_BY = {
        "fake_number": {"V1"},
        "dropped_source": {"V7"},
        "provisional_as_final": {"V4"},
        "missing_risks": {"V3"},
        "stale_hidden": {"V2", "V8"},
        "double_count": {"V9"},
        "rounded_miss": {"V6"},
        "approval_bypass": {"V5"},
    }

    def test_there_are_exactly_the_eight_faults_the_architecture_lists(self):
        assert set(FAULTS) == set(self.DETECTED_BY)

    def test_the_contract_make_acceptance_measures_against_is_this_one(self):
        assert {fault: set(checks) for fault, checks in CAUGHT_BY.items()} == self.DETECTED_BY

    @pytest.mark.parametrize("fault", sorted(DETECTED_BY))
    def test_the_fault_is_detected_by_its_check(self, fault, clean, context):
        report = validate(apply_fault(clean, fault, context), context)
        assert not report.passed, f"{fault} slipped through"
        assert self.DETECTED_BY[fault] <= failing_ids(report), (fault, failing_ids(report))

    @pytest.mark.parametrize("fault", sorted(DETECTED_BY))
    def test_a_fault_does_not_make_unrelated_checks_fail(self, fault, clean, context):
        # a precise gate points at the real problem, not at everything
        report = validate(apply_fault(clean, fault, context), context)
        # a figure that lost its sources is also seen by V1, because a headline token points at it
        allowed = self.DETECTED_BY[fault] | ({"V1"} if fault == "dropped_source" else set())
        assert failing_ids(report) <= allowed, (fault, failing_ids(report))

    def test_validation_never_modifies_the_brief_it_checks(self, clean, context):
        before = clean.model_dump_json()
        validate(clean, context)
        assert clean.model_dump_json() == before

    def test_the_attempt_number_is_recorded_on_the_report(self, clean, context):
        assert validate(clean, context, attempt=3).attempt == 3


def test_a_kpi_without_a_value_is_expected_to_be_undefined(clean, context):
    blank = [
        f.model_copy(update={"value": None, "variance_abs": None, "variance_pct": None})
        if f.key == "AC_CO"
        else f
        for f in clean.kpis
    ]
    v6 = next(
        c
        for c in validate(clean.model_copy(update={"kpis": tuple(blank)}), context).checks
        if c.id == "V6"
    )
    assert not v6.passed  # it says met, but it has no value to be met with
    fixed = [
        f.model_copy(update={"status": KpiStatus.UNDEFINED}) if f.key == "AC_CO" else f
        for f in blank
    ]
    assert "V6" not in failing_ids(
        validate(clean.model_copy(update={"kpis": tuple(fixed)}), context)
    )
