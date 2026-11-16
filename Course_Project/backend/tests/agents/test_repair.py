"""Lab 10: diagnose, then regenerate only what failed, inside a bounded budget (rule 8)."""

import pytest

from app.agents.compose import compose_brief, off_target
from app.agents.llm import FakeLLM
from app.agents.repair import RepairContext, repair, validate_and_repair
from app.agents.skills.options_skill import draft_option_set
from app.agents.validation.faults import FAULTS, apply_fault
from app.agents.validation.suite import ValidationContext, validate


@pytest.fixture(scope="module")
def vctx(store, connector, plan):
    return ValidationContext(
        plan=plan,
        facts=store.facts_by_id,
        sources=store.sources,
        publications=tuple(connector.get_publications(store.current_period)),
        definitions={d.key: d for d in store.definitions},
    )


@pytest.fixture(scope="module")
def rctx(plan, figures, health):
    return RepairContext(
        plan=plan,
        figures={f.key: f for f in figures},
        health=tuple(health),
        model=FakeLLM("drafter"),
    )


@pytest.fixture(scope="module")
def clean(plan, figures, health):
    model = FakeLLM("drafter")
    return compose_brief(
        plan, figures, [draft_option_set(model, f) for f in off_target(figures)], health
    )


@pytest.mark.parametrize("fault", FAULTS)
def test_every_injected_fault_is_repaired_within_the_budget(fault, clean, vctx, rctx):
    broken = apply_fault(clean, fault, vctx)
    assert not validate(broken, vctx).passed
    fixed, report, history = validate_and_repair(broken, vctx, rctx, max_attempts=3)
    assert report.passed, [(c.id, [v.message for v in c.violations]) for c in report.failing]
    assert len(history) <= 3  # the first look plus at most two repairs


@pytest.mark.parametrize("fault", FAULTS)
def test_the_repaired_brief_matches_a_brief_that_was_never_broken_where_nothing_failed(
    fault, clean, vctx, rctx
):
    fixed, _, _ = validate_and_repair(apply_fault(clean, fault, vctx), vctx, rctx, max_attempts=3)
    assert fixed.kpis == clean.kpis
    assert fixed.summary == clean.summary
    assert fixed.assumptions == clean.assumptions
    assert fixed.data_health == clean.data_health
    assert fixed.claims_status == "draft"


def test_only_the_failing_options_are_regenerated(clean, vctx, rctx):
    broken = apply_fault(clean, "fake_number", vctx)  # breaks the first KPI's first option only
    report = validate(broken, vctx)
    fixed, log = repair(broken, report, rctx, attempt=2)
    first, rest = fixed.option_sets[0], fixed.option_sets[1:]
    assert first.attempt == 2  # regenerated
    assert rest == clean.option_sets[1:]  # untouched, same objects and content
    assert any("options" in line and first.kpi_key in line for line in log)


def test_a_corrupted_figure_is_rebuilt_from_the_engine_not_patched(clean, vctx, rctx):
    broken = apply_fault(clean, "rounded_miss", vctx)
    report = validate(broken, vctx)
    fixed, log = repair(broken, report, rctx, attempt=2)
    figure = next(f for f in fixed.kpis if f.key == "PL_PCT")
    assert figure == rctx.figures["PL_PCT"]
    assert any("figure" in line and "PL_PCT" in line for line in log)


def test_a_document_that_claims_approval_is_reset_to_draft(clean, vctx, rctx):
    broken = apply_fault(clean, "approval_bypass", vctx)
    fixed, log = repair(broken, validate(broken, vctx), rctx, attempt=2)
    assert fixed.claims_status == "draft"
    assert any("draft" in line for line in log)


def test_repair_passes_the_diagnosis_to_the_model_so_it_can_correct_itself(clean, vctx):
    seen = []

    class Listening(FakeLLM):
        def complete(self, task, payload, schema=None):
            seen.append(payload)
            return super().complete(task, payload)

    rctx = RepairContext(
        plan=vctx.plan,
        figures={f.key: f for f in clean.kpis},
        health=(),
        model=Listening("drafter"),
    )
    broken = apply_fault(clean, "fake_number", vctx)
    repair(broken, validate(broken, vctx), rctx, attempt=2)
    assert seen and "12" in (seen[0]["diagnosis"] or "")
    assert seen[0]["attempt"] == 2
    assert seen[0]["inject"] == []  # repair never injects a fault


class _StubbornlyWrong(FakeLLM):
    """A model that keeps writing a number by hand, however many times it is told not to."""

    def complete(self, task, payload, schema=None):
        out = super().complete(task, {**payload, "attempt": 1, "inject": ["fake_number"]})
        return out


def test_when_repair_cannot_fix_it_the_loop_stops_at_the_budget_and_says_so(
    clean, vctx, plan, figures, health, monkeypatch
):
    rctx = RepairContext(
        plan=plan,
        figures={f.key: f for f in figures},
        health=tuple(health),
        model=_StubbornlyWrong("drafter"),
    )
    broken = apply_fault(clean, "fake_number", vctx)

    from app.agents import repair as repair_module

    calls = []
    real_validate = repair_module.validate

    def counting(doc, ctx, attempt=1):
        calls.append(attempt)
        return real_validate(doc, ctx, attempt)

    monkeypatch.setattr(repair_module, "validate", counting)
    _, report, history = validate_and_repair(broken, vctx, rctx, max_attempts=3)

    assert not report.passed  # escalated: still failing, handed to a person with the diagnosis
    assert calls == [1, 2, 3]  # three looks, never a fourth
    assert len(history) == 3
    assert report.failing and report.failing[0].violations[0].diagnosis


def test_a_clean_brief_needs_no_repair(clean, vctx, rctx):
    fixed, report, history = validate_and_repair(clean, vctx, rctx, max_attempts=3)
    assert report.passed and fixed == clean and len(history) == 1


def test_a_regenerated_set_keeps_two_or_three_options(clean, vctx, rctx):
    fixed, _, _ = validate_and_repair(
        apply_fault(clean, "missing_risks", vctx), vctx, rctx, max_attempts=3
    )
    for option_set in fixed.option_sets:
        assert 2 <= len(option_set.options) <= 3
        assert all(o.risks and o.trade_offs and o.assumptions for o in option_set.options)
