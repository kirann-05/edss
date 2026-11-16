import json
import re

import pytest

from app.agents.compose import off_target
from app.agents.skills.options_skill import draft_option_set, option_payload
from app.agents.tokens import lint_numbers, unresolved_refs


def by_key(figures, key):
    return next(f for f in figures if f.key == key)


class TestWhatTheModelIsTold:
    def test_the_model_is_never_sent_a_figure(self, figures):
        # rule 1: the model does not produce, compute or even see a number
        for figure in figures:
            payload = option_payload(figure)
            payload.pop("attempt")
            assert re.search(r"\d", json.dumps(payload)) is None, figure.key
            assert not any(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in payload.values()
            )

    def test_status_direction_and_trend_arrive_as_words(self, figures):
        payload = option_payload(by_key(figures, "PL_PCT"))
        assert payload["status"] == "missed"
        assert payload["direction"] == "below_target"
        assert payload["trend"] in {"improving", "declining", "flat", "unknown"}

    def test_flagged_departments_are_named_so_the_options_can_respect_them(self, figures):
        payload = option_payload(by_key(figures, "PL_PCT"))
        assert payload["flags"]["stale"] == ["CIVIL"]
        assert payload["flags"]["undefined"] == ["AIML"]


class TestDrafting:
    def test_a_miss_gets_three_options_and_an_at_risk_kpi_gets_two(self, model, figures):
        assert len(draft_option_set(model, by_key(figures, "PL_PCT")).options) == 3
        assert len(draft_option_set(model, by_key(figures, "AC_PASS_PCT")).options) == 2

    def test_every_option_states_assumptions_risks_and_trade_offs(self, model, figures):
        for figure in off_target(figures):
            for option in draft_option_set(model, figure).options:
                assert option.assumptions and option.risks and option.trade_offs, option.id
                assert option.title.strip() and option.description.strip()

    def test_option_ids_are_stable_and_name_their_kpi(self, model, figures):
        ids = [o.id for o in draft_option_set(model, by_key(figures, "PL_PCT")).options]
        assert ids == ["PL_PCT-1", "PL_PCT-2", "PL_PCT-3"]

    def test_text_holds_no_hand_written_figure_and_every_token_resolves(
        self, model, figures, render_context
    ):
        for figure in figures:
            for option in draft_option_set(model, figure).options:
                fields = [
                    option.title,
                    option.description,
                    *option.assumptions,
                    *option.risks,
                    *option.trade_offs,
                ]
                for text in fields:
                    assert lint_numbers(text) == [], (option.id, text)
                    assert unresolved_refs(text, render_context) == [], (option.id, text)

    def test_the_same_skill_serves_every_domain_with_no_code_change(self, model, figures):
        domains = {draft_option_set(model, f).options[0].title for f in figures}
        assert len(domains) >= 4  # academic, research, placement, finance each read differently

    def test_the_stale_department_is_named_in_the_first_options_assumptions(self, model, figures):
        first = draft_option_set(model, by_key(figures, "PL_PCT")).options[0]
        assert any("CIVIL" in a and "stale" in a for a in first.assumptions)


class TestFailureInjection:
    """A model that misbehaves on its first attempt, to give validation something real to catch."""

    def test_a_fake_number_appears_on_the_first_attempt_only(self, model, figures):
        figure = by_key(figures, "PL_PCT")
        bad = draft_option_set(model, figure, inject=["fake_number"], attempt=1)
        assert any(lint_numbers(o.description) for o in bad.options)
        good = draft_option_set(
            model, figure, inject=["fake_number"], attempt=2, diagnosis="digits found"
        )
        assert not any(lint_numbers(o.description) for o in good.options)

    def test_missing_risks_appear_on_the_first_attempt_only(self, model, figures):
        figure = by_key(figures, "PL_PCT")
        assert (
            draft_option_set(model, figure, inject=["missing_risks"], attempt=1).options[0].risks
            == ()
        )
        assert draft_option_set(model, figure, inject=["missing_risks"], attempt=2).options[0].risks

    def test_a_provisional_figure_described_as_confirmed_appears_on_the_first_attempt_only(
        self, model, figures
    ):
        figure = by_key(figures, "PL_PCT")
        bad = draft_option_set(
            model, figure, inject=["provisional_as_final"], fault_fact_id=7, attempt=1
        )
        assert "{{fact:7}} confirmed" in bad.options[0].description
        good = draft_option_set(
            model, figure, inject=["provisional_as_final"], fault_fact_id=7, attempt=2
        )
        assert "{{fact:7}}" not in good.options[0].description

    def test_no_fault_is_injected_unless_asked(self, model, figures):
        figure = by_key(figures, "PL_PCT")
        for option in draft_option_set(model, figure, attempt=1).options:
            assert option.risks and lint_numbers(option.description) == []

    def test_the_attempt_number_is_recorded_so_a_repaired_set_can_be_told_apart(
        self, model, figures
    ):
        assert draft_option_set(model, by_key(figures, "PL_PCT"), attempt=2).attempt == 2


def test_an_unknown_task_is_a_loud_error_not_a_silent_blank(model):
    with pytest.raises(KeyError, match="no handler"):
        model.complete("write_a_poem", {})
