from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.enums import Domain, FactStatus
from app.domain.models import MetricFact


def fact(value):
    return MetricFact(
        id=1,
        batch_id=1,
        domain=Domain.FINANCE,
        metric_key="fin.budget_sanctioned",
        dept_code="A",
        period_year="2025-26",
        period_sub="FY",
        value=value,
        unit="INR lakh",
        status=FactStatus.FINAL,
        as_of="2026-09-01",
        source_system_id=1,
        source_ref="t:1",
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("74.96"), "74.96"),
        (Decimal("1E+2"), "100"),  # str(Decimal("1E+2")) would be "1E+2"
        (Decimal("1E-7"), "0.0000001"),
        (Decimal("-0.04"), "-0.04"),
        (Decimal("100"), "100"),
    ],
)
def test_decimals_serialise_as_plain_strings_never_exponents_or_floats(value, expected):
    assert fact(value).model_dump(mode="json")["value"] == expected


def test_records_are_immutable():
    with pytest.raises(ValidationError, match="frozen"):
        fact(Decimal(1)).value = Decimal(2)  # type: ignore[misc]
