"""Restricted formula evaluator for KPI definitions (decision D8, security note in ARCHITECTURE).

A KPI formula is data, written by a person and stored in a definition row. It is parsed with
Python's own parser and then checked against an allow-list. Nothing is ever passed to eval,
so a formula cannot import, call, index or reach an attribute.

Grammar
  number        1, 100, 0.5                         (converted from text, never a binary float)
  operators     + - * /  and unary + -
  sum("key")                         total over the departments being evaluated
  mean("key")                        simple mean over those departments
  weighted_mean("key", "weight_key") sum(key * weight) / sum(weight)
  unique_publications()              publications counted once, however many departments share them

A zero denominator makes the result UNDEFINED. UNDEFINED flows through any further arithmetic,
so a KPI is never shown as 0 or 100 because a department had nothing to divide by.
"""

import ast
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from decimal import Context, Decimal, localcontext
from typing import Protocol

from app.domain.models import DecimalStr, Frozen, MetricSpec

MAX_SOURCE_LENGTH = 300
MAX_CONSTANT = 10**9

# function name -> number of arguments
FUNCTIONS: dict[str, int] = {
    "sum": 1,
    "mean": 1,
    "weighted_mean": 2,
    "unique_publications": 0,
}

# The publication count of a department is derived from this metric, so its presence is what
# makes a department eligible for a formula that counts publications (trap T2).
PUBLICATION_METRIC = "res.publications_count"


class FormulaError(ValueError):
    """The formula is not valid, or uses something outside the allowed grammar."""


class _Undefined:
    def __repr__(self) -> str:
        return "UNDEFINED"


UNDEFINED = _Undefined()
Value = Decimal | _Undefined


class InputTerm(Frozen):
    """One aggregate a formula used, kept so the drill-down can show where a figure came from."""

    label: str
    value: DecimalStr


@dataclass(frozen=True)
class ParsedFormula:
    source: str
    tree: ast.Expression
    required_keys: frozenset[str]
    uses_publications: bool


class FormulaInputs(Protocol):
    def metric(self, dept: str, key: str) -> Decimal:
        """One department's figure for a metric, with sub-periods already combined."""
        ...

    def publication_count(self, depts: Collection[str]) -> int:
        """Distinct publications credited to at least one of these departments."""
        ...


def parse_formula(source: str, known_metrics: Mapping[str, MetricSpec]) -> ParsedFormula:
    if len(source) > MAX_SOURCE_LENGTH:
        raise FormulaError(f"formula is longer than {MAX_SOURCE_LENGTH} characters")
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except (SyntaxError, RecursionError) as error:
        raise FormulaError(f"syntax error: {error}") from error

    keys: set[str] = set()
    uses_publications = False

    def check(node: ast.AST) -> None:
        nonlocal uses_publications
        match node:
            case ast.BinOp(
                left=left, op=ast.Add() | ast.Sub() | ast.Mult() | ast.Div(), right=right
            ):
                check(left)
                check(right)
            case ast.UnaryOp(op=ast.UAdd() | ast.USub(), operand=operand):
                check(operand)
            case ast.Constant(value=value) if type(value) in (int, float):
                if abs(value) > MAX_CONSTANT:
                    raise FormulaError("number is too large for a KPI formula")
            case ast.Call(func=ast.Name(id=name), args=args, keywords=keywords):
                if name not in FUNCTIONS:
                    raise FormulaError(f"unknown function {name!r}")
                if keywords:
                    raise FormulaError(f"{name} does not take keyword arguments")
                if len(args) != FUNCTIONS[name]:
                    raise FormulaError(f"{name} takes {FUNCTIONS[name]} arguments, got {len(args)}")
                for arg in args:
                    match arg:
                        case ast.Constant(value=str() as key):
                            if key not in known_metrics:
                                raise FormulaError(f"unknown metric {key!r}")
                            keys.add(key)
                        case _:
                            raise FormulaError(f"arguments of {name} must be quoted metric keys")
                if name == "unique_publications":
                    uses_publications = True
                    keys.add(PUBLICATION_METRIC)
            case _:
                raise FormulaError(f"{type(node).__name__} is not allowed in a formula")

    check(tree.body)
    return ParsedFormula(
        source=source.strip(),
        tree=tree,
        required_keys=frozenset(keys),
        uses_publications=uses_publications,
    )


def evaluate(
    parsed: ParsedFormula,
    depts: Sequence[str],
    inputs: FormulaInputs,
    terms: list[InputTerm] | None = None,
) -> Value:
    """Evaluate over a set of departments. `terms` collects each aggregate used, once each."""
    scope = tuple(depts)

    def note(label: str, value: Decimal) -> None:
        if terms is not None and all(term.label != label for term in terms):
            terms.append(InputTerm(label=label, value=value))

    def call(name: str, args: list[str]) -> Value:
        if name == "sum":
            total = sum((inputs.metric(d, args[0]) for d in scope), Decimal(0))
            note(f"sum({args[0]})", total)
            return total
        if name == "mean":
            if not scope:
                return UNDEFINED
            mean = sum((inputs.metric(d, args[0]) for d in scope), Decimal(0)) / len(scope)
            note(f"mean({args[0]})", mean)
            return mean
        if name == "weighted_mean":
            value_key, weight_key = args
            weight_total = sum((inputs.metric(d, weight_key) for d in scope), Decimal(0))
            if weight_total == 0:
                return UNDEFINED
            weighted = sum(
                (inputs.metric(d, value_key) * inputs.metric(d, weight_key) for d in scope),
                Decimal(0),
            )
            result = weighted / weight_total
            note(f"weighted_mean({value_key}, {weight_key})", result)
            return result
        count = Decimal(inputs.publication_count(scope))
        note("unique_publications()", count)
        return count

    def walk(node: ast.AST) -> Value:
        match node:
            case ast.Constant(value=value):
                return Decimal(str(value))
            case ast.UnaryOp(op=op, operand=operand):
                inner = walk(operand)
                if isinstance(inner, _Undefined):
                    return UNDEFINED
                return -inner if isinstance(op, ast.USub) else inner
            case ast.BinOp(left=left, op=op, right=right):
                a, b = walk(left), walk(right)
                if isinstance(a, _Undefined) or isinstance(b, _Undefined):
                    return UNDEFINED
                if isinstance(op, ast.Add):
                    return a + b
                if isinstance(op, ast.Sub):
                    return a - b
                if isinstance(op, ast.Mult):
                    return a * b
                return UNDEFINED if b == 0 else a / b
            case ast.Call(func=ast.Name(id=name), args=args):
                return call(name, [arg.value for arg in args if isinstance(arg, ast.Constant)])
        raise FormulaError("formula was not validated")  # unreachable after parse_formula

    with localcontext(Context(prec=28)):
        return walk(parsed.tree.body)
