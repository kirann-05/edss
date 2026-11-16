import pytest

from app.kpi.describe import describe_formula
from app.kpi.loader import load_seed_definitions


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        (
            '100 * sum("acad.students_passed") / sum("acad.students_appeared")',
            "100 × total students passed ÷ total students appeared",
        ),
        (
            'weighted_mean("acad.co_attainment", "acad.courses_total")',
            "CO attainment level weighted by courses offered",
        ),
        ('mean("acad.po_attainment")', "average PO attainment level"),
        (
            'unique_publications() / sum("ref.faculty_count")',
            "unique publications ÷ total faculty",
        ),
        ('sum("fin.revenue_actual")', "total revenue (actual)"),
        ('(sum("res.grant_count") + 2) * 3', "(total grants sanctioned + 2) × 3"),
        ('-sum("res.grant_count")', "-total grants sanctioned"),
    ],
)
def test_formulas_read_in_plain_language(formula, expected):
    assert describe_formula(formula) == expected


def test_every_seed_formula_can_be_described():
    for definition in load_seed_definitions():
        text = describe_formula(definition.formula)
        assert text and "sum(" not in text and '"' not in text


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("sum(acad.students_passed)", "Total students passed"),
        ("mean(acad.po_attainment)", "Average PO attainment level"),
        (
            "weighted_mean(acad.co_attainment, acad.courses_total)",
            "CO attainment level, weighted by courses offered",
        ),
        ("unique_publications()", "Unique publications"),
        (
            "something_else(x)",
            "something_else(x)",
        ),  # an unknown term is shown as it is, never hidden
    ],
)
def test_an_input_term_reads_in_plain_language(label, expected):
    from app.kpi.describe import describe_term

    assert describe_term(label) == expected
