from decimal import Decimal

import pytest

from app.agents.models import FactFigure, KpiFigure
from app.agents.tokens import (
    Ref,
    RenderContext,
    lint_numbers,
    parse_tokens,
    render_segments,
    render_text,
)
from app.domain.enums import FactStatus, KpiStatus
from app.kpi.results import KpiFlags


def kpi(key="PL_PCT", value="74.96", target="75", status=KpiStatus.MISSED, unit="%", precision=1):
    return KpiFigure(
        key=key, name="Placement percentage", domain="placement", unit=unit, precision=precision,
        higher_is_better=True, placeholder=True, definition_active=True, definition_approved=False,
        kpi_version=1, period_year="2025-26", value=Decimal(value) if value else None,
        target=Decimal(target), variance_abs=Decimal(value) - Decimal(target) if value else None,
        variance_pct=None, status=status, inputs=(), input_fact_ids=(1, 2), as_of=None,
        flags=KpiFlags(),
    )  # fmt: skip


def fact(fid=7, status=FactStatus.FINAL):
    return FactFigure(
        id=fid, label="Students registered", dept_code="CSE", value=Decimal("313"), unit="students",
        status=status, source_ref="v_placement_summary:CSE",
    )  # fmt: skip


@pytest.fixture
def ctx():
    return RenderContext(
        kpis={"PL_PCT": kpi()},
        facts={7: fact(), 8: fact(8, FactStatus.PENDING_RECONCILIATION)},
    )


class TestParse:
    def test_plain_text_has_no_references(self):
        assert parse_tokens("No figures here") == ["No figures here"]

    def test_a_kpi_token_defaults_to_its_value(self):
        assert parse_tokens("is {{kpi:PL_PCT}} now") == [
            "is ",
            Ref("kpi", "PL_PCT", "value"),
            " now",
        ]

    @pytest.mark.parametrize("field", ["target", "gap", "status", "value"])
    def test_a_kpi_token_can_name_a_field(self, field):
        assert parse_tokens(f"{{{{kpi:PL_PCT.{field}}}}}") == [Ref("kpi", "PL_PCT", field)]

    def test_a_fact_token_names_a_record(self):
        assert parse_tokens("{{fact:7}}") == [Ref("fact", "7", "value")]

    def test_spacing_inside_the_braces_is_tolerated(self):
        assert parse_tokens("{{ kpi : PL_PCT }}") == [Ref("kpi", "PL_PCT", "value")]

    def test_a_malformed_token_is_left_as_text_so_the_lint_can_see_it(self):
        assert parse_tokens("{{kpi:}} and {{what:1}}") == ["{{kpi:}} and {{what:1}}"]


class TestRender:
    def test_text_is_resolved_from_the_figures_never_from_the_model(self, ctx):
        text = render_text(
            "{{kpi:PL_PCT}} against {{kpi:PL_PCT.target}}: {{kpi:PL_PCT.status}}, {{kpi:PL_PCT.gap}}",
            ctx,
        )
        assert text == "75.0% against 75.0%: Missed, 0.04 pts below target"

    def test_a_fact_is_rendered_with_its_unit(self, ctx):
        assert render_text("{{fact:7}}", ctx) == "313 students"

    def test_segments_carry_what_the_ui_needs_to_make_a_figure_clickable_and_badged(self, ctx):
        segments = render_segments("Placement {{kpi:PL_PCT}} from {{fact:8}}", ctx)
        assert [s.t for s in segments] == ["text", "ref", "text", "ref"]
        figure = segments[1]
        assert (figure.kind, figure.key, figure.field, figure.display) == (
            "kpi",
            "PL_PCT",
            "value",
            "75.0%",
        )
        assert figure.status == "missed"
        record = segments[3]
        assert record.kind == "fact" and record.status == "pending_reconciliation"

    def test_an_unknown_reference_is_marked_unresolved_not_invented(self, ctx):
        segment = render_segments("{{kpi:NOPE}}", ctx)[0]
        assert segment.unresolved is True
        assert segment.display == "{{kpi:NOPE}}"

    def test_an_undefined_value_renders_as_n_a(self):
        context = RenderContext(kpis={"PL_PCT": kpi(value=None)}, facts={})
        assert render_text("{{kpi:PL_PCT}}", context) == "n/a"


class TestNumberLint:
    """Check V1: model text may hold digits only inside reference tokens (decision D21 adds words)."""

    def test_text_made_only_of_words_and_tokens_is_clean(self):
        assert lint_numbers("Placement is {{kpi:PL_PCT}} against {{kpi:PL_PCT.target}}.") == []

    @pytest.mark.parametrize(
        "text",
        [
            "Raise registration by 12%",
            "We expect about 1,250 students",
            "A gap of 3.4 points",
            "Hit 75 by March",
        ],
    )
    def test_a_stray_digit_is_caught(self, text):
        assert lint_numbers(text), text

    @pytest.mark.parametrize(
        "text",
        [
            "Three departments are behind",
            "Nearly half of the offers are provisional",
            "A twenty percent rise",
            "Double the internship hours",
            "About two lakh in extra spend",
            "One department has no record",
            "Zero students were placed",
        ],
    )
    def test_a_spelled_out_number_is_caught_too(self, text):
        assert lint_numbers(text), text

    @pytest.mark.parametrize(
        "text",
        [
            "One of the departments is stale",
            "No one has approved this",
            "Someone from the cell should confirm it",
            "Each option stands on its own",
            "It is left out and never counted as zero",
            "A gap that is different from zero",
        ],
    )
    def test_ordinary_prose_that_merely_contains_the_word_one_is_not_flagged(self, text):
        assert lint_numbers(text) == [], text

    @pytest.mark.parametrize(
        "text",
        [
            "For 2025-26 the target stands",
            "Data was last updated on 2026-09-21",
            "Revenue for Q3 is still forecast",
            "Semester S2 results are in",
        ],
    )
    def test_labels_that_name_a_period_or_date_are_allowed(self, text):
        assert lint_numbers(text) == [], text

    def test_a_digit_hidden_inside_an_unresolvable_looking_token_is_still_caught(self):
        assert lint_numbers("{{kpi:PL_PCT}} rose 5% {{kpi:PL_PCT.target}}")

    def test_the_fragments_found_are_returned_so_the_diagnosis_can_quote_them(self):
        assert lint_numbers("up 12% and 3 more") == ["12", "3"]
