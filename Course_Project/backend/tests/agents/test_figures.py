"""The Python renderer must format figures exactly as the dashboard does.

Both suites run shared/figure-vectors.json. If they ever disagree about rounding, one fails.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.agents.figures import (
    format_exact,
    format_number,
    format_variance,
    format_with_unit,
    hides_miss,
    round_decimal,
)
from app.domain.enums import KpiStatus

VECTORS = json.loads((Path(__file__).parents[3] / "shared" / "figure-vectors.json").read_text())


def dec(value):
    return None if value is None else Decimal(value)


@pytest.mark.parametrize("v", VECTORS["round_decimal"], ids=lambda v: f"{v['value']}@{v['places']}")
def test_round_decimal(v):
    assert round_decimal(Decimal(v["value"]), v["places"]) == v["expected"]


@pytest.mark.parametrize("v", VECTORS["format_number"], ids=lambda v: f"{v['value']}@{v['places']}")
def test_format_number(v):
    assert format_number(dec(v["value"]), v["places"]) == v["expected"]


@pytest.mark.parametrize("v", VECTORS["format_with_unit"], ids=lambda v: f"{v['value']}{v['unit']}")
def test_format_with_unit(v):
    assert format_with_unit(dec(v["value"]), v["places"], v["unit"]) == v["expected"]


@pytest.mark.parametrize("v", VECTORS["format_variance"], ids=lambda v: str(v["variance_abs"]))
def test_format_variance(v):
    assert format_variance(dec(v["variance_abs"]), v["precision"], v["unit"]) == v["expected"]


@pytest.mark.parametrize(
    "v", VECTORS["rounding_hides_miss"], ids=lambda v: f"{v['value']}v{v['target']}"
)
def test_hides_miss(v):
    got = hides_miss(dec(v["value"]), dec(v["target"]), v["precision"], KpiStatus(v["status"]))
    assert got is v["expected"]


@pytest.mark.parametrize("v", VECTORS["format_exact"], ids=lambda v: v["value"])
def test_format_exact(v):
    assert format_exact(Decimal(v["value"])) == v["expected"]
