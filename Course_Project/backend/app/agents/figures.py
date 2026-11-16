"""Display formatting for figures, the Python twin of frontend/src/lib/format.ts.

The two must agree exactly, so both run shared/figure-vectors.json. Rounding is half away from
zero on Decimal, which is what the UI does on strings, and never goes through a float.
Rule 5: a missed target is never hidden by rounding.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import KpiStatus

MAX_VARIANCE_PLACES = 4


def round_decimal(value: Decimal, places: int) -> str:
    """Fixed places as text, half away from zero. A value that rounds to zero is just zero."""
    rounded = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    if rounded == 0:
        rounded = abs(rounded)  # never "-0.0"
    return format(rounded, "f")


def _group(whole: str) -> str:
    return f"{int(whole):,}"


def format_number(value: Decimal | None, places: int) -> str:
    """Grouped with fixed places. An undefined value is n/a, never zero."""
    if value is None:
        return "n/a"
    rounded = round_decimal(value, places)
    negative = rounded.startswith("-")
    whole, _, fraction = (rounded[1:] if negative else rounded).partition(".")
    return f"{'-' if negative else ''}{_group(whole)}{'.' + fraction if fraction else ''}"


def format_with_unit(value: Decimal | None, places: int, unit: str) -> str:
    figure = format_number(value, places)
    if value is None or unit == "":
        return figure
    return f"{figure}%" if unit == "%" else f"{figure} {unit}"


def format_exact(value: Decimal) -> str:
    """The exact figure without a long tail: up to four places, trailing zeros removed."""
    rounded = round_decimal(value, MAX_VARIANCE_PLACES)
    return rounded.rstrip("0").rstrip(".") if "." in rounded else rounded


def format_variance(variance_abs: Decimal | None, precision: int, unit: str) -> str:
    """Words for the gap to target. Adds places until a real shortfall is visible."""
    if variance_abs is None:
        return "no target gap"
    if variance_abs == 0:
        return "on target"
    direction = "below target" if variance_abs < 0 else "above target"
    magnitude = abs(variance_abs)
    unit_text = "pts" if unit == "%" else unit

    def words(amount: str) -> str:
        return " ".join(part for part in (amount, unit_text, direction) if part)

    for places in range(precision, MAX_VARIANCE_PLACES + 1):
        rounded = round_decimal(magnitude, places)
        if Decimal(rounded) != 0:
            return words(rounded)
    return words(f"under {round_decimal(Decimal('0.0001'), MAX_VARIANCE_PLACES)}")


def hides_miss(
    value: Decimal | None, target: Decimal | None, precision: int, status: KpiStatus
) -> bool:
    """True when a missed KPI would read as equal to its target at the display precision."""
    if status is not KpiStatus.MISSED or value is None or target is None:
        return False
    return round_decimal(value, precision) == round_decimal(target, precision)
