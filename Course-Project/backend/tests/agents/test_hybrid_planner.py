"""The hybrid planner (decision D30): rules first, the model second, the person where they disagree."""

import pytest

from app.agents.llm import LLMUnavailable
from app.agents.models import Clarification
from app.agents.skills.plan_skill import DISAGREE, KpiInfo, PlanCatalogue, clarify, propose_plan
from app.domain.enums import Domain
from tests.agents.test_real_model_skills import Scripted, plan_answer


@pytest.fixture(scope="module")
def catalogue(store):
    return PlanCatalogue(
        periods=store.periods,
        current_period=store.current_period,
        kpis=tuple(KpiInfo(key=d.key, name=d.name, domain=d.domain) for d in store.definitions),
    )


QUESTION = {"text": "Which?", "why": "Because."}


def asks(*ids):
    return {"questions": [{"id": i, **QUESTION, "choices": ["a"]} for i in ids]}


class Down(Scripted):
    def complete(self, task, payload, schema=None):
        raise LLMUnavailable("the model server is not there")


class Nonsense(Scripted):
    def complete(self, task, payload, schema=None):
        self.payloads.append(payload)
        return "not json"


def test_when_the_words_say_everything_the_model_is_not_asked_at_all(catalogue):
    model = Scripted()  # an empty script: any call would fail
    request = "Placement brief for the Governing Council for 2025-26"
    assert clarify(model, request, [], catalogue) == []
    plan = propose_plan(model, request, [], catalogue)
    assert model.payloads == []
    assert plan.domains == (Domain.PLACEMENT,) and plan.audience == "Governing Council review"


def test_a_model_that_over_asks_is_overruled_by_the_words(catalogue):
    # the evaluation's commonest model mistake: asking for a period the request names
    model = Scripted(asks("period", "scope", "audience"))
    asked = clarify(model, "Research update for 2024-25", [], catalogue)
    assert [q.id for q in asked] == ["audience"]  # the words name the period and the area


def test_what_the_words_do_not_say_is_asked_even_if_the_model_thinks_it_was_said(catalogue):
    model = Scripted(asks())  # the model asks nothing, as if the request were complete
    asked = clarify(model, "Prepare the brief", [], catalogue)
    assert [q.id for q in asked] == ["period", "scope", "audience"]
    assert all(q.why.endswith(DISAGREE) for q in asked)


def test_where_both_find_something_missing_it_is_asked_plainly(catalogue):
    model = Scripted(asks("period", "scope", "audience"))
    asked = clarify(model, "Prepare the brief", [], catalogue)
    assert [q.id for q in asked] == ["period", "scope", "audience"]
    assert not any(DISAGREE in q.why for q in asked)


def test_options_for_every_kpi_is_never_the_models_guess(catalogue):
    model = Scripted(plan_answer(options_for="all", domains=["finance"], kpi_keys=[]))
    plan = propose_plan(model, "Prepare the brief", [], catalogue)
    assert plan.options_for == "off_target"


def test_after_skipped_questions_the_models_reading_fills_only_what_the_words_left_open(catalogue):
    model = Scripted(
        plan_answer(
            period_year="2024-25",
            domains=["finance"],
            kpi_keys=[],
            audience="Governing Council review",
        )
    )
    plan = propose_plan(model, "Brief for the Registrar", [], catalogue)
    assert plan.period_year == "2024-25" and plan.domains == (Domain.FINANCE,)
    assert plan.audience == "Internal leadership review"  # the words said Registrar


def test_answers_count_as_words(catalogue):
    answers = [
        Clarification(question_id="period", answer="2023-24"),
        Clarification(question_id="scope", answer="Academic"),
        Clarification(question_id="audience", answer="Internal leadership review"),
    ]
    model = Scripted()
    assert clarify(model, "Prepare the brief", answers, catalogue) == []
    assert propose_plan(model, "Prepare the brief", answers, catalogue).period_year == "2023-24"


def test_if_the_model_talks_nonsense_planning_carries_on_with_the_rules(catalogue):
    model = Nonsense()
    asked = clarify(model, "Prepare the brief", [], catalogue)
    assert [q.id for q in asked] == ["period", "scope", "audience"]
    assert len(model.payloads) == 3  # the first try and two repairs, then the rules
    plan = propose_plan(Nonsense(), "Prepare the brief", [], catalogue)
    assert plan.period_year == catalogue.current_period and len(plan.domains) == 4


def test_if_the_model_server_is_down_it_is_said_at_once(catalogue):
    # drafting will need it, so carrying on would only fail later and further from the cause
    with pytest.raises(LLMUnavailable):
        clarify(Down(), "Prepare the brief", [], catalogue)
