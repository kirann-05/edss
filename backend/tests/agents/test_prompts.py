import json

import pytest

from app.agents.prompts import SYSTEM, UnknownTask, build_messages


def test_every_task_a_model_is_given_has_a_prompt():
    assert set(SYSTEM) == {"clarify", "propose_plan", "revise_plan", "draft_options"}


@pytest.mark.parametrize("task", sorted(SYSTEM))
def test_every_prompt_carries_the_rule_about_numbers_and_asks_for_json_only(task):
    system = build_messages(task, {})[0]["content"]
    assert "Never write a number" in system
    assert "Answer only with JSON" in system
    assert "You are never told any figure" in system


def test_the_payload_goes_in_as_json_and_a_task_has_exactly_two_messages():
    messages = build_messages("clarify", {"request": "Prepare the brief", "answers": []})
    assert [m["role"] for m in messages] == ["system", "user"]
    assert json.loads(messages[1]["content"]) == {"request": "Prepare the brief", "answers": []}


def test_failure_injection_never_reaches_the_model():
    visible = json.loads(
        build_messages("draft_options", {"a": 1, "inject": ["fake_number"], "fault_fact_id": 5})[1][
            "content"
        ]
    )
    assert visible == {"a": 1}


def test_the_options_prompt_names_the_only_tokens_a_model_may_use():
    system = build_messages("draft_options", {})[0]["content"]
    for token in ("{{kpi:KEY}}", "{{kpi:KEY.target}}", "{{kpi:KEY.gap}}", "{{kpi:KEY.status}}"):
        assert token in system
    assert "Never write {{fact:...}}" in system
    assert "diagnosis" in system and "validation_error" in system


def test_the_plan_prompts_leave_the_steps_to_code():
    for task in ("propose_plan", "revise_plan"):
        assert "empty list for steps" in build_messages(task, {})[0]["content"]


def test_a_task_with_no_prompt_is_refused():
    with pytest.raises(UnknownTask):
        build_messages("summarise", {})


CATALOGUE = {"periods": ["2023-24", "2024-25", "2025-26"], "current_period": "2025-26", "kpis": []}


def roles(task, payload):
    return [m["role"] for m in build_messages(task, payload)]


class TestWorkedExamples:
    def payload(self, **over):
        return {"request": "x", "answers": [], "catalogue": CATALOGUE, **over}

    def test_planning_tasks_get_examples_as_earlier_turns_before_the_real_input(self):
        assert roles("clarify", self.payload()) == ["system"] + ["user", "assistant"] * 4 + ["user"]
        assert roles("propose_plan", self.payload()) == ["system"] + ["user", "assistant"] * 4 + [
            "user"
        ]

    def test_the_last_message_is_always_the_real_input(self):
        last = build_messages("propose_plan", self.payload(request="Prepare the brief"))[-1]
        assert json.loads(last["content"])["request"] == "Prepare the brief"

    def test_the_examples_use_the_real_periods_so_they_cannot_disagree_with_the_data(self):
        answers = [
            json.loads(m["content"])
            for m in build_messages("propose_plan", self.payload())
            if m["role"] == "assistant"
        ]
        used = {a["period_year"] for a in answers}
        assert used <= set(CATALOGUE["periods"])
        assert "2024-25" in used and "2025-26" in used  # "last year" is worked out, not copied

    def test_the_example_plans_leave_the_kpis_and_steps_to_code(self):
        for message in build_messages("propose_plan", self.payload()):
            if message["role"] == "assistant":
                answer = json.loads(message["content"])
                assert answer["kpi_keys"] == [] and answer["steps"] == []

    def test_a_request_that_names_everything_gets_no_questions_in_the_clarify_examples(self):
        answers = [
            json.loads(m["content"])
            for m in build_messages("clarify", self.payload())
            if m["role"] == "assistant"
        ]
        assert {"questions": []} in answers
        assert any(len(a["questions"]) == 3 for a in answers)

    def test_examples_never_reuse_a_request_the_evaluation_scores_a_model_on(self):
        from importlib.util import module_from_spec, spec_from_file_location
        from pathlib import Path

        path = Path(__file__).resolve().parents[3] / "scripts" / "evaluate_llm.py"
        spec = spec_from_file_location("evaluate_llm", path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        scored = {case.request.lower() for case in module.CASES}
        for task in ("clarify", "propose_plan"):
            shown = {
                json.loads(m["content"])["request"].lower()
                for m in build_messages(task, self.payload())
                if m["role"] == "user"
            }
            assert not (shown - {"x"}) & scored, task

    def test_no_examples_when_there_is_no_catalogue_to_build_them_from(self):
        assert roles("clarify", {"request": "x"}) == ["system", "user"]
        assert roles("draft_options", self.payload()) == ["system", "user"]

    def test_the_repair_counter_is_for_the_machinery_and_never_shown_to_the_model(self):
        shown = json.loads(
            build_messages("draft_options", {"kpi_key": "X", "repair_round": 2})[-1]["content"]
        )
        assert "repair_round" not in shown
