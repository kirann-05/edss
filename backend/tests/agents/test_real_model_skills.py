"""What the skills do with a real model's output, which unlike the FakeLLM can be wrong.

A scripted stand-in plays the model: it returns the answers it is given, in order, and records
what it was asked. Nothing here needs a network or a real model.
"""

from typing import Any

import pytest

from app.agents.llm import LLMOutputError, structured_call
from app.agents.models import Clarification
from app.agents.skills.options_skill import OptionSetDraft, draft_option_set
from app.agents.skills.plan_skill import (
    KpiInfo,
    PlanCatalogue,
    PlanDraft,
    clarify,
    propose_plan,
    revise_plan,
)
from app.domain.enums import Domain


class Scripted:
    """A model that is not the FakeLLM. It answers from a script and keeps the payloads."""

    provider = "scripted"
    name = "scripted"

    def __init__(self, *answers: dict[str, Any]):
        self.answers = list(answers)
        self.payloads: list[dict[str, Any]] = []

    def complete(self, task, payload, schema=None):
        self.payloads.append(payload)
        return self.answers.pop(0)

    def generate(self, task, payload, schema, max_repairs=2, check=None):
        return structured_call(self, task, payload, schema, max_repairs, check)


@pytest.fixture(scope="module")
def catalogue(store):
    return PlanCatalogue(
        periods=store.periods,
        current_period=store.current_period,
        kpis=tuple(KpiInfo(key=d.key, name=d.name, domain=d.domain) for d in store.definitions),
    )


def plan_answer(**over):
    answer = {
        "period_year": "2025-26",
        "domains": ["placement"],
        "kpi_keys": ["PL_PCT", "PL_AVG"],
        "options_for": "off_target",
        "audience": "Internal leadership review",
        "steps": [],
    }
    answer.update(over)
    return answer


class TestClarifyWithARealModel:
    def question(self, id_, **over):
        return {"id": id_, "text": f"Question {id_}?", "why": "Because.", "choices": [], **over}

    def test_only_the_three_things_a_plan_can_use_are_ever_asked(self, catalogue):
        model = Scripted(
            {"questions": [self.question("period"), self.question("favourite_colour")]}
        )
        assert [q.id for q in clarify(model, "x", [], catalogue)] == ["period"]

    def test_an_answered_question_is_not_asked_again_whatever_the_model_says(self, catalogue):
        model = Scripted({"questions": [self.question("period"), self.question("scope")]})
        asked = clarify(
            model, "x", [Clarification(question_id="period", answer="2025-26")], catalogue
        )
        assert [q.id for q in asked] == ["scope"]

    def test_a_model_that_never_stops_asking_cannot_keep_the_conversation_going(self, catalogue):
        every = {
            "questions": [
                self.question(i) for i in ("period", "scope", "audience", "more", "again")
            ]
        }
        answers = [
            Clarification(question_id=i, answer="x") for i in ("period", "scope", "audience")
        ]
        assert clarify(Scripted(every), "x", answers, catalogue) == []

    def test_a_repeated_id_is_asked_once(self, catalogue):
        model = Scripted({"questions": [self.question("scope"), self.question("scope")]})
        assert len(clarify(model, "x", [], catalogue)) == 1

    def test_period_choices_come_from_the_catalogue_not_from_the_model(self, catalogue):
        model = Scripted({"questions": [self.question("period", choices=["2099-00", "1066"])]})
        (q,) = clarify(model, "x", [], catalogue)
        assert q.choices == tuple(reversed(catalogue.periods))

    def test_a_question_with_no_reason_is_sent_back_to_the_model(self, catalogue):
        model = Scripted(
            {"questions": [self.question("period", why=" ")]},
            {"questions": [self.question("period")]},
        )
        assert [q.id for q in clarify(model, "x", [], catalogue)] == ["period"]
        assert "needs both a text and a why" in model.payloads[1]["validation_error"]


class TestPlanFromARealModel:
    def test_the_steps_are_written_in_code_whatever_the_model_writes(self, catalogue):
        wild = plan_answer(steps=[{"id": "x", "title": "Email the dean", "detail": "Send it"}])
        plan = propose_plan(Scripted(wild), "x", [], catalogue)
        assert "Email the dean" not in [s.title for s in plan.steps]
        assert [s.id for s in plan.steps] == [
            "access",
            "aggregate",
            "synthesise",
            "options",
            "validate",
            "review",
        ]

    def test_the_areas_follow_from_the_kpis_not_from_the_models_list(self, catalogue):
        # the model says only academic, but chose a placement KPI: code goes by the KPIs
        plan = propose_plan(
            Scripted(plan_answer(domains=["academic"], kpi_keys=["PL_PCT", "AC_CO"])),
            "x",
            [],
            catalogue,
        )
        assert plan.domains == (Domain.ACADEMIC, Domain.PLACEMENT)
        assert plan.kpi_keys == ("AC_CO", "PL_PCT")  # catalogue order

    def test_with_no_kpis_chosen_the_areas_decide_them(self, catalogue):
        plan = propose_plan(
            Scripted(plan_answer(domains=["finance"], kpi_keys=[])), "x", [], catalogue
        )
        assert plan.domains == (Domain.FINANCE,)
        assert set(plan.kpi_keys) == set(catalogue.keys_for([Domain.FINANCE]))

    def test_repeated_kpis_are_kept_once(self, catalogue):
        plan = propose_plan(
            Scripted(plan_answer(kpi_keys=["PL_PCT", "PL_PCT"])), "x", [], catalogue
        )
        assert plan.kpi_keys == ("PL_PCT",)

    def test_an_invented_kpi_is_sent_back_with_the_real_ones_to_choose_from(self, catalogue):
        model = Scripted(plan_answer(kpi_keys=["PL_PCT", "NIRF_42"]), plan_answer())
        plan = propose_plan(model, "x", [], catalogue)
        assert plan.kpi_keys == ("PL_PCT", "PL_AVG")
        assert "unknown kpi_keys ['NIRF_42']" in model.payloads[1]["validation_error"]

    def test_a_period_we_have_no_data_for_is_sent_back(self, catalogue):
        model = Scripted(plan_answer(period_year="2031-32"), plan_answer())
        assert propose_plan(model, "x", [], catalogue).period_year == "2025-26"
        assert "2031-32" in model.payloads[1]["validation_error"]

    def test_an_audience_the_system_does_not_have_is_sent_back(self, catalogue):
        model = Scripted(plan_answer(audience="Everyone"), plan_answer())
        assert propose_plan(model, "x", [], catalogue).audience == "Internal leadership review"
        assert "audience must be exactly one of" in model.payloads[1]["validation_error"]

    def test_a_model_that_cannot_make_a_valid_plan_is_stopped_after_the_budget(self, catalogue):
        model = Scripted(*[plan_answer(period_year="1999-00")] * 5)
        with pytest.raises(LLMOutputError):
            propose_plan(model, "x", [], catalogue)
        assert len(model.payloads) == 3

    def test_a_revision_is_checked_the_same_way(self, catalogue):
        first = propose_plan(Scripted(plan_answer()), "x", [], catalogue)
        model = Scripted(plan_answer(kpi_keys=["MADE_UP"]), plan_answer(kpi_keys=["PL_PCT"]))
        revised, changes = revise_plan(model, first, "only the placement percentage", catalogue)
        assert revised.kpi_keys == ("PL_PCT",) and revised.revision == 2
        assert changes  # worked out in code, not taken from the model


def option(**over):
    base = {
        "title": "Intensify training",
        "description": "{{kpi:PL_PCT}} is {{kpi:PL_PCT.gap}}. Focus training where conversion is lowest.",
        "assumptions": ["Students attend."],
        "risks": ["Faculty load."],
        "trade_offs": ["Depth against breadth."],
    }
    base.update(over)
    return base


def answer(first=None):
    """Two options, the schema's minimum. The first can be replaced with one that has a problem."""
    return {"options": [first or option(), option(title="Widen recruiters")]}


class TestOptionsFromARealModel:
    @pytest.fixture
    def figure(self, figures):
        return next(f for f in figures if f.key == "PL_PCT")

    def test_a_clean_answer_is_taken_as_it_is(self, figure):
        model = Scripted(answer())
        result = draft_option_set(model, figure)
        assert [o.id for o in result.options] == ["PL_PCT-1", "PL_PCT-2"]
        assert len(model.payloads) == 1

    def test_a_number_written_by_hand_is_sent_back_naming_it(self, figure):
        model = Scripted(answer(option(description="Raise it by 12% within a year.")), answer())
        draft_option_set(model, figure)
        assert "(12)" in model.payloads[1]["validation_error"]
        assert "reference tokens" in model.payloads[1]["validation_error"]

    def test_a_spelled_out_number_is_sent_back_too(self, figure):
        model = Scripted(answer(option(risks=["About two departments may resist."])), answer())
        draft_option_set(model, figure)
        assert "two" in model.payloads[1]["validation_error"]

    def test_a_token_for_another_kpi_is_not_allowed(self, figure):
        model = Scripted(
            answer(option(description="Compare with {{kpi:AC_CO}} next year.")), answer()
        )
        draft_option_set(model, figure)
        assert "token that is not allowed" in model.payloads[1]["validation_error"]

    def test_a_record_token_is_not_allowed_because_the_model_was_given_no_records(self, figure):
        model = Scripted(
            answer(option(description="{{fact:8841}} confirmed placements.")), answer()
        )
        draft_option_set(model, figure)
        assert "fact:8841" in model.payloads[1]["validation_error"]

    @pytest.mark.parametrize("field", ["assumptions", "risks", "trade_offs"])
    def test_an_option_with_an_empty_list_is_sent_back(self, figure, field):
        model = Scripted(answer(option(**{field: []})), answer())
        draft_option_set(model, figure)
        assert f"at least one entry in {field}" in model.payloads[1]["validation_error"]

    def test_the_diagnosis_from_a_failed_gate_is_passed_on_for_the_redraft(self, figure):
        model = Scripted(answer())
        draft_option_set(
            model, figure, attempt=2, diagnosis="V4: provisional offers described as confirmed"
        )
        assert model.payloads[0]["diagnosis"] == "V4: provisional offers described as confirmed"
        assert model.payloads[0]["attempt"] == 2

    def test_demo_faults_are_applied_in_code_to_a_real_models_answer(self, figure):
        model = Scripted(answer())
        result = draft_option_set(model, figure, inject=["fake_number", "missing_risks"])
        assert "12%" in result.options[0].description
        assert result.options[0].risks == ()
        assert "inject" not in model.payloads[0] or model.payloads[0]["inject"] == []

    def test_demo_faults_are_applied_once_not_to_the_redraft(self, figure):
        model = Scripted(answer())
        result = draft_option_set(model, figure, attempt=2, inject=["fake_number"])
        assert "12%" not in result.options[0].description

    def test_a_record_fault_names_the_record_it_was_given(self, figure):
        result = draft_option_set(
            Scripted(answer()), figure, inject=["provisional_as_final"], fault_fact_id=8841
        )
        assert "{{fact:8841}}" in result.options[0].description

    def test_the_schema_demands_two_or_three_options(self):
        with pytest.raises(Exception, match="at least 2|too_short"):
            OptionSetDraft.model_validate({"options": [option()]})
        assert PlanDraft.model_validate(plan_answer()).steps == []
