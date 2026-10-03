"""Lab 1 and Lab 3: clarify, plan, revise and lock, as one case-agnostic skill (FR-1)."""

from datetime import UTC, datetime

import pytest

from app.agents.llm import FakeLLM
from app.agents.models import Clarification
from app.agents.skills.plan_skill import (
    KpiInfo,
    PlanCatalogue,
    PlanError,
    apply_patch,
    clarify,
    diff_plans,
    lock_plan,
    propose_plan,
    revise_plan,
)
from app.domain.enums import Domain

PERIODS = ("2023-24", "2024-25", "2025-26")


@pytest.fixture(scope="module")
def catalogue(store):
    return PlanCatalogue(
        periods=store.periods,
        current_period=store.current_period,
        kpis=tuple(KpiInfo(key=d.key, name=d.name, domain=d.domain) for d in store.definitions),
    )


@pytest.fixture
def model():
    return FakeLLM("clarifier")


def ids(questions):
    return [q.id for q in questions]


class TestClarify:
    def test_a_vague_request_gets_at_least_two_clarifying_questions(self, model, catalogue):
        questions = clarify(model, "Prepare the leadership brief", [], catalogue)
        assert len(questions) >= 2
        assert set(ids(questions)) >= {"period", "scope"}

    def test_every_question_says_why_it_is_being_asked(self, model, catalogue):
        for q in clarify(model, "Prepare the brief", [], catalogue):
            assert q.text.strip() and q.why.strip()

    def test_period_and_scope_questions_offer_the_real_choices(self, model, catalogue):
        by_id = {q.id: q for q in clarify(model, "Prepare the brief", [], catalogue)}
        assert by_id["period"].choices == tuple(reversed(PERIODS))
        assert "All four areas" in by_id["scope"].choices

    def test_a_specific_request_is_asked_nothing_it_already_answered(self, model, catalogue):
        request = "Governing Council brief for 2025-26 covering placement and finance"
        assert clarify(model, request, [], catalogue) == []

    def test_a_partly_specific_request_is_asked_only_what_is_missing(self, model, catalogue):
        questions = clarify(model, "A brief on placement for 2024-25", [], catalogue)
        assert ids(questions) == ["audience"]

    def test_an_answered_question_is_never_asked_again(self, model, catalogue):
        first = clarify(model, "Prepare the brief", [], catalogue)
        answers = [Clarification(question_id="period", answer="2024-25")]
        second = clarify(model, "Prepare the brief", answers, catalogue)
        assert "period" in ids(first) and "period" not in ids(second)
        assert set(ids(second)) == set(ids(first)) - {"period"}

    def test_answering_everything_ends_the_questions(self, model, catalogue):
        answers = [
            Clarification(question_id="period", answer="2025-26"),
            Clarification(question_id="scope", answer="All four areas"),
            Clarification(question_id="audience", answer="Governing Council review"),
        ]
        assert clarify(model, "Prepare the brief", answers, catalogue) == []


class TestPlan:
    def test_the_plan_follows_the_answers(self, model, catalogue):
        answers = [
            Clarification(question_id="period", answer="2024-25"),
            Clarification(question_id="scope", answer="Placement and Finance"),
            Clarification(question_id="audience", answer="Governing Council review"),
        ]
        plan = propose_plan(model, "Prepare the brief", answers, catalogue)
        assert plan.period_year == "2024-25"
        assert set(plan.domains) == {Domain.PLACEMENT, Domain.FINANCE}
        assert plan.audience == "Governing Council review"
        assert set(plan.kpi_keys) == {
            "PL_PCT",
            "PL_AVG",
            "PL_INT",
            "FN_UTIL",
            "FN_GRANT_UTIL",
            "FN_REV",
        }
        assert plan.locked_at is None and plan.revision == 1

    def test_unanswered_slots_fall_back_to_plain_defaults(self, model, catalogue):
        plan = propose_plan(model, "Prepare the brief", [], catalogue)
        assert plan.period_year == catalogue.current_period
        assert set(plan.domains) == {
            Domain.ACADEMIC,
            Domain.RESEARCH,
            Domain.PLACEMENT,
            Domain.FINANCE,
        }
        assert len(plan.kpi_keys) == 13

    def test_the_same_skill_serves_two_different_requests_with_no_code_change(
        self, model, catalogue
    ):
        a = propose_plan(model, "Placement brief for the Council, 2024-25", [], catalogue)
        b = propose_plan(
            model, "Internal review of research and academic results for 2025-26", [], catalogue
        )
        assert (a.period_year, set(a.domains)) == ("2024-25", {Domain.PLACEMENT})
        assert (b.period_year, set(b.domains)) == ("2025-26", {Domain.RESEARCH, Domain.ACADEMIC})
        assert a.audience != b.audience
        assert set(a.kpi_keys).isdisjoint(b.kpi_keys)

    def test_the_outline_has_stable_step_ids_a_person_can_edit(self, model, catalogue):
        plan = propose_plan(model, "Prepare the brief", [], catalogue)
        assert [s.id for s in plan.steps] == [
            "access",
            "aggregate",
            "synthesise",
            "options",
            "validate",
            "review",
        ]
        assert all(s.title and s.detail for s in plan.steps)

    def test_off_target_options_are_the_default(self, model, catalogue):
        assert propose_plan(model, "Prepare the brief", [], catalogue).options_for == "off_target"


class TestRevise:
    @pytest.fixture
    def plan(self, model, catalogue):
        return propose_plan(
            model, "Governing Council brief for 2025-26 on everything", [], catalogue
        )

    def test_dropping_a_domain_removes_its_kpis_and_says_so(self, model, catalogue, plan):
        revised, changes = revise_plan(model, plan, "Drop finance please", catalogue)
        assert Domain.FINANCE not in revised.domains
        assert not any(k.startswith("FN_") for k in revised.kpi_keys)
        assert any("Finance" in c and "Dropped" in c for c in changes)

    def test_a_revision_keeps_the_same_steps_rather_than_replacing_them(
        self, model, catalogue, plan
    ):
        revised, _ = revise_plan(model, plan, "Only placement", catalogue)
        assert [s.id for s in revised.steps] == [s.id for s in plan.steps]
        assert revised.steps != plan.steps  # the wording followed the new scope

    def test_the_revision_number_goes_up_and_the_plan_stays_unlocked(self, model, catalogue, plan):
        revised, _ = revise_plan(model, plan, "Add nothing special", catalogue)
        assert revised.revision == plan.revision + 1 and revised.locked_at is None

    def test_two_rounds_of_feedback_build_on_each_other(self, model, catalogue, plan):
        one, _ = revise_plan(model, plan, "Only placement and finance", catalogue)
        two, changes = revise_plan(
            model, one, "Make it for the 2024-25 period and every KPI", catalogue
        )
        assert two.revision == 3
        assert set(two.domains) == {Domain.PLACEMENT, Domain.FINANCE}
        assert two.period_year == "2024-25" and two.options_for == "all"
        assert any("2024-25" in c for c in changes)

    def test_feedback_that_changes_nothing_reports_no_changes(self, model, catalogue, plan):
        _, changes = revise_plan(model, plan, "Looks good to me", catalogue)
        assert changes == []

    def test_a_kpi_can_be_dropped_by_name(self, model, catalogue, plan):
        revised, changes = revise_plan(model, plan, "Exclude AC_PO", catalogue)
        assert "AC_PO" not in revised.kpi_keys and "AC_CO" in revised.kpi_keys
        assert any("Average PO attainment" in c for c in changes)


class TestManualEdit:
    @pytest.fixture
    def plan(self, model, catalogue):
        return propose_plan(model, "Prepare the brief", [], catalogue)

    def test_a_person_can_change_the_scope_directly(self, catalogue, plan):
        edited = apply_patch(
            plan, {"period_year": "2024-25", "kpi_keys": ["PL_PCT", "AC_CO"]}, catalogue
        )
        assert edited.period_year == "2024-25" and edited.kpi_keys == ("PL_PCT", "AC_CO")
        assert edited.revision == plan.revision + 1

    def test_a_step_can_be_reworded_without_changing_its_id(self, catalogue, plan):
        edited = apply_patch(plan, {"steps": {"review": {"title": "Registrar review"}}}, catalogue)
        step = next(s for s in edited.steps if s.id == "review")
        assert step.title == "Registrar review" and step.detail  # detail kept

    @pytest.mark.parametrize(
        "patch",
        [
            {"period_year": "1999-00"},
            {"kpi_keys": ["NOT_A_KPI"]},
            {"kpi_keys": []},
            {"domains": []},
            {"options_for": "sometimes"},
            {"steps": {"nope": {"title": "x"}}},
        ],
    )
    def test_nonsense_is_refused_with_a_reason(self, catalogue, plan, patch):
        with pytest.raises(PlanError):
            apply_patch(plan, patch, catalogue)


class TestLock:
    def test_locking_stamps_the_plan(self, model, catalogue):
        plan = propose_plan(model, "Prepare the brief", [], catalogue)
        at = datetime(2026, 10, 3, 12, tzinfo=UTC)
        locked = lock_plan(plan, at)
        assert locked.locked and locked.locked_at == at
        assert locked.kpi_keys == plan.kpi_keys

    def test_a_locked_plan_cannot_be_edited_or_revised(self, model, catalogue):
        locked = lock_plan(
            propose_plan(model, "Prepare the brief", [], catalogue), datetime.now(UTC)
        )
        with pytest.raises(PlanError, match="locked"):
            apply_patch(locked, {"period_year": "2024-25"}, catalogue)
        with pytest.raises(PlanError, match="locked"):
            revise_plan(model, locked, "Drop finance", catalogue)

    def test_a_plan_cannot_be_locked_twice(self, model, catalogue):
        locked = lock_plan(
            propose_plan(model, "Prepare the brief", [], catalogue), datetime.now(UTC)
        )
        with pytest.raises(PlanError, match="already locked"):
            lock_plan(locked, datetime.now(UTC))


def test_diff_plans_describes_each_kind_of_change(model, catalogue):
    old = propose_plan(model, "Prepare the brief", [], catalogue)
    new = apply_patch(
        old,
        {"period_year": "2024-25", "options_for": "all", "audience": "Governing Council review"},
        catalogue,
    )
    changes = diff_plans(old, new, catalogue)
    assert "Period set to 2024-25" in changes
    assert any("every KPI" in c for c in changes)
    assert any("Governing Council review" in c for c in changes)
