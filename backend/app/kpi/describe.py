"""Plain-language rendering of a KPI formula, for the drill-down ("show the formula").

Only presentation. The formula that is evaluated is always the raw one in the definition.
"""

import ast

from app.kpi.catalogue import CATALOGUE
from app.kpi.formulas import FormulaError, parse_formula

_SYMBOL = {ast.Add: "+", ast.Sub: "-", ast.Mult: "×", ast.Div: "÷"}
_PRECEDENCE = {ast.Add: 1, ast.Sub: 1, ast.Mult: 2, ast.Div: 2}


def _label(key: str) -> str:
    label = CATALOGUE[key].label
    # "Students passed" reads better in a sentence as "students passed", but keep "CO attainment"
    return label[0].lower() + label[1:] if len(label) > 1 and label[1].islower() else label


def _render(node: ast.AST) -> str:
    match node:
        case ast.Constant(value=value):
            return str(value)
        case ast.UnaryOp(op=op, operand=operand):
            sign = "-" if isinstance(op, ast.USub) else ""
            return f"{sign}{_render(operand)}"
        case ast.BinOp(left=left, op=op, right=right):
            rank = _PRECEDENCE[type(op)]

            def side(child: ast.AST, tighter: bool) -> str:
                text = _render(child)
                if isinstance(child, ast.BinOp):
                    child_rank = _PRECEDENCE[type(child.op)]
                    if child_rank < rank or (tighter and child_rank == rank):
                        return f"({text})"
                return text

            return f"{side(left, False)} {_SYMBOL[type(op)]} {side(right, True)}"
        case ast.Call(func=ast.Name(id=name), args=args):
            keys = [a.value for a in args if isinstance(a, ast.Constant)]
            if name == "sum":
                return f"total {_label(keys[0])}"
            if name == "mean":
                return f"average {_label(keys[0])}"
            if name == "weighted_mean":
                return f"{_label(keys[0])} weighted by {_label(keys[1])}"
            return "unique publications"
    raise FormulaError("cannot describe this formula")


def describe_formula(formula: str) -> str:
    return _render(parse_formula(formula, CATALOGUE).tree.body)


def describe_term(label: str) -> str:
    """Plain-language name for an input term such as 'sum(plc.registered)'."""
    name, _, rest = label.partition("(")
    args = [a.strip() for a in rest.rstrip(")").split(",") if a.strip()]
    try:
        if name == "sum":
            text = f"total {_label(args[0])}"
        elif name == "mean":
            text = f"average {_label(args[0])}"
        elif name == "weighted_mean":
            text = f"{_label(args[0])}, weighted by {_label(args[1])}"
        elif name == "unique_publications":
            text = "unique publications"
        else:
            return label
    except (IndexError, KeyError):
        return label
    return text[:1].upper() + text[1:]
