from decimal import Decimal

import pytest

from app.kpi.catalogue import CATALOGUE
from app.kpi.formulas import UNDEFINED, FormulaError, evaluate, parse_formula

PASS_PCT = '100 * sum("acad.students_passed") / sum("acad.students_appeared")'


class FakeInputs:
    """Per-department values already combined across sub-periods, plus publication credit."""

    def __init__(self, values, pubs=None):
        self.values = values
        self.pubs = pubs or {}

    def metric(self, dept, key):
        return Decimal(self.values[(dept, key)])

    def publication_count(self, depts):
        return len({p for d in depts for p in self.pubs.get(d, ())})


def run(source, depts, values, pubs=None, terms=None):
    parsed = parse_formula(source, CATALOGUE)
    return evaluate(parsed, depts, FakeInputs(values, pubs), terms)


class TestEvaluation:
    def test_percentages_are_aggregated_from_totals_not_averaged(self):
        # rule 11, trap T7: a small department with a high rate must not pull the average up
        values = {
            ("BIG", "acad.students_passed"): "800",
            ("BIG", "acad.students_appeared"): "1000",
            ("SMALL", "acad.students_passed"): "49",
            ("SMALL", "acad.students_appeared"): "50",
        }
        institution = run(PASS_PCT, ["BIG", "SMALL"], values)
        assert institution == Decimal("849") * 100 / Decimal("1050")
        naive_mean = (Decimal(80) + Decimal(98)) / 2  # 89, the wrong answer
        assert abs(institution - naive_mean) > Decimal("8")  # the weighted value is 80.86

    def test_arithmetic_is_decimal_exact(self):
        values = {
            ("A", "plc.placed_confirmed"): "1874",
            ("A", "plc.registered"): "2500",
        }
        value = run('100 * sum("plc.placed_confirmed") / sum("plc.registered")', ["A"], values)
        assert value == Decimal("74.96")
        assert isinstance(value, Decimal)

    def test_decimal_constants_are_not_binary_floats(self):
        values = {("A", "res.grant_count"): "1"}
        assert run('sum("res.grant_count") * 0.1 + 0.2', ["A"], values) == Decimal("0.3")

    def test_zero_denominator_is_undefined_never_zero_or_hundred(self):
        # trap T9
        values = {
            ("A", "plc.placed_confirmed"): "0",
            ("A", "plc.registered"): "0",
        }
        assert (
            run('100 * sum("plc.placed_confirmed") / sum("plc.registered")', ["A"], values)
            is UNDEFINED
        )

    def test_undefined_propagates_through_further_arithmetic(self):
        values = {("A", "plc.placed_confirmed"): "0", ("A", "plc.registered"): "0"}
        source = '1 + 100 * sum("plc.placed_confirmed") / sum("plc.registered")'
        assert run(source, ["A"], values) is UNDEFINED

    def test_subtraction_and_a_negative_result(self):
        # a surplus as IQAC may define one: revenue less expenditure, which can go below zero
        values = {("A", "fin.revenue_actual"): "120.5", ("A", "fin.expenditure_actual"): "130"}
        source = 'sum("fin.revenue_actual") - sum("fin.expenditure_actual")'
        assert run(source, ["A"], values) == Decimal("-9.5")

    def test_unary_minus_and_plus(self):
        values = {("A", "fin.revenue_actual"): "4"}
        assert run('-sum("fin.revenue_actual") + 10', ["A"], values) == Decimal("6")
        assert run('+sum("fin.revenue_actual")', ["A"], values) == Decimal("4")

    def test_undefined_stays_undefined_under_a_minus_sign(self):
        values = {("A", "plc.placed_confirmed"): "0", ("A", "plc.registered"): "0"}
        source = '-(sum("plc.placed_confirmed") / sum("plc.registered"))'
        assert run(source, ["A"], values) is UNDEFINED

    def test_mean_and_weighted_mean(self):
        values = {
            ("A", "acad.po_attainment"): "2",
            ("B", "acad.po_attainment"): "3",
            ("A", "acad.co_attainment"): "2",
            ("B", "acad.co_attainment"): "3",
            ("A", "acad.courses_total"): "30",
            ("B", "acad.courses_total"): "10",
        }
        assert run('mean("acad.po_attainment")', ["A", "B"], values) == Decimal("2.5")
        weighted = run(
            'weighted_mean("acad.co_attainment", "acad.courses_total")', ["A", "B"], values
        )
        assert weighted == Decimal("2.25")  # (2*30 + 3*10) / 40

    def test_weighted_mean_with_no_weight_is_undefined(self):
        values = {("A", "acad.co_attainment"): "2", ("A", "acad.courses_total"): "0"}
        assert (
            run('weighted_mean("acad.co_attainment", "acad.courses_total")', ["A"], values)
            is UNDEFINED
        )

    def test_mean_over_no_departments_is_undefined(self):
        assert run('mean("acad.po_attainment")', [], {}) is UNDEFINED

    def test_unique_publications_counts_a_shared_paper_once(self):
        # trap T5: one DOI credited to two departments
        pubs = {"CSE": {"doi:1", "doi:2", "doi:shared"}, "ECE": {"doi:3", "doi:shared"}}
        assert run("unique_publications()", ["CSE", "ECE"], {}, pubs) == Decimal(4)
        assert run("unique_publications()", ["CSE"], {}, pubs) == Decimal(3)
        assert run("unique_publications()", ["ECE"], {}, pubs) == Decimal(2)

    def test_per_faculty_ratio_uses_only_the_given_departments(self):
        values = {("A", "ref.faculty_count"): "10", ("B", "ref.faculty_count"): "30"}
        pubs = {"A": {"p1", "p2"}, "B": {"p3"}}
        source = 'unique_publications() / sum("ref.faculty_count")'
        assert run(source, ["A", "B"], values, pubs) == Decimal("0.075")
        assert run(source, ["A"], values, pubs) == Decimal("0.2")

    def test_aggregates_are_recorded_as_terms_once_each(self):
        values = {
            ("A", "acad.students_passed"): "9",
            ("A", "acad.students_appeared"): "10",
        }
        terms = []
        run(PASS_PCT + ' + 0 * sum("acad.students_passed")', ["A"], values, terms=terms)
        assert [(t.label, t.value) for t in terms] == [
            ("sum(acad.students_passed)", Decimal("9")),
            ("sum(acad.students_appeared)", Decimal("10")),
        ]


class TestParsing:
    def test_required_keys_are_extracted(self):
        parsed = parse_formula(PASS_PCT, CATALOGUE)
        assert parsed.required_keys == {"acad.students_passed", "acad.students_appeared"}
        assert parsed.uses_publications is False

    def test_publications_function_requires_the_publication_count_metric(self):
        parsed = parse_formula('unique_publications() / sum("ref.faculty_count")', CATALOGUE)
        assert parsed.uses_publications is True
        assert parsed.required_keys == {"res.publications_count", "ref.faculty_count"}

    def test_unknown_metric_key_is_rejected(self):
        with pytest.raises(FormulaError, match="unknown metric"):
            parse_formula('sum("acad.not_a_metric")', CATALOGUE)

    def test_wrong_number_of_arguments_is_rejected(self):
        with pytest.raises(FormulaError, match="argument"):
            parse_formula('weighted_mean("acad.co_attainment")', CATALOGUE)
        with pytest.raises(FormulaError, match="argument"):
            parse_formula("unique_publications(1)", CATALOGUE)

    def test_unknown_function_is_rejected(self):
        with pytest.raises(FormulaError, match="function"):
            parse_formula('median("acad.co_attainment")', CATALOGUE)

    def test_syntax_error_is_a_formula_error(self):
        with pytest.raises(FormulaError, match="syntax"):
            parse_formula("100 * (", CATALOGUE)

    def test_a_formula_longer_than_the_limit_is_refused_before_parsing(self):
        source = " + ".join(['sum("acad.students_passed")'] * 20)
        assert len(source) > 300
        with pytest.raises(FormulaError, match="longer than 300"):
            parse_formula(source, CATALOGUE)


@pytest.mark.parametrize(
    "source",
    [
        "__import__('os').system('echo pwned')",
        'sum("acad.students_passed").__class__',
        'open("/etc/passwd")',
        "[x for x in range(10)]",
        "lambda: 1",
        '"a" + "b"',
        "2 ** 999999999",
        "10 % 3",
        "10 // 3",
        "x + 1",
        'sum(sum("acad.students_passed"))',
        'sum("acad.students_passed", "acad.students_appeared")',
        "True + 1",
        "1 if 1 else 2",
        'sum(key="acad.students_passed")',
        "1_000_000_000_000_000_000_000_000_000 * 3",
        "f'{1}'",
        "(1).real",
    ],
)
def test_nothing_but_the_whitelisted_grammar_is_accepted(source):
    with pytest.raises(FormulaError):
        parse_formula(source, CATALOGUE)
