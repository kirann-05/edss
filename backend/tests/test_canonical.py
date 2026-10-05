"""The canonical text form the audit chain hashes: the same content must always give the same text."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum

import pytest

from app.core.canonical import canonical
from app.domain.enums import KpiStatus
from app.domain.models import Department


def test_key_order_does_not_change_the_text():
    assert canonical({"b": 1, "a": {"y": 2, "x": 3}}) == canonical({"a": {"x": 3, "y": 2}, "b": 1})


def test_a_decimal_is_written_as_exact_text_never_a_float():
    assert canonical({"v": Decimal("74.96")}) == '{"v":"74.96"}'
    assert canonical({"v": Decimal("0.1") + Decimal("0.2")}) == '{"v":"0.3"}'


def test_dates_and_times_are_iso_text():
    when = datetime(2026, 10, 6, 9, 30, tzinfo=UTC)
    assert canonical([date(2026, 10, 6), when]) == '["2026-10-06","2026-10-06T09:30:00+00:00"]'


class Shade(Enum):
    RED = "red"


def test_an_enum_is_written_as_its_value():
    assert canonical({"shade": Shade.RED}) == '{"shade":"red"}'
    assert canonical({"status": KpiStatus.MISSED}) == '{"status":"missed"}'


def test_a_set_is_sorted_so_its_order_cannot_change_the_hash():
    assert canonical({"depts": {"MECH", "CSE", "AIML"}}) == '{"depts":["AIML","CSE","MECH"]}'
    assert canonical(frozenset({3, 1, 2})) == canonical([1, 2, 3])


def test_a_tuple_is_written_as_a_list():  # json does this itself, so canonical needs no case for it
    assert canonical({"ids": (3, 1)}) == '{"ids":[3,1]}'


def test_a_model_is_written_as_its_json_fields():
    dept = Department(code="CSE", name="Computer Science and Engineering", school="Engineering")
    assert canonical(dept) == canonical(dept.model_dump(mode="json"))


def test_a_value_it_cannot_write_is_refused_not_silently_dropped():
    with pytest.raises(TypeError, match="cannot serialise a value of type object"):
        canonical({"x": object()})
