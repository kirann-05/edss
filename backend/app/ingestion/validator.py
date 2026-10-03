"""The ingest validator: what is allowed in, and a plain reason for everything that is not.

docs/DATA_CONTRACT.md section 7: rows without a status or an as-of date are rejected, rejects are
counted and reported, never swallowed, and every accepted row keeps its source reference. Nothing
here corrects a figure. A row is either right as it stands or it is refused with its reason, so
the data owner can fix it at the source.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.domain.enums import Domain, FactStatus
from app.ingestion.rows import RawRow
from app.kpi.catalogue import CATALOGUE

PERIOD = re.compile(r"^\d{4}-\d{2}$")
SUB_PERIODS = ("S1", "S2", "Q1", "Q2", "Q3", "Q4", "AY", "FY")
STATUS_WORDS = ", ".join(s.value for s in FactStatus)


@dataclass(frozen=True)
class Reject:
    ref: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class FactRow:
    ref: str
    dept_code: str
    metric_key: str
    period_year: str
    period_sub: str
    value: Decimal
    numerator: Decimal | None
    denominator: Decimal | None
    unit: str
    status: FactStatus
    as_of: date
    source_ref: str  # what the source called it, or where in the source it was


@dataclass(frozen=True)
class PublicationRow:
    ref: str
    dedup_key: str
    title: str
    venue: str
    period_year: str
    indexing: str
    status: FactStatus
    dept_codes: tuple[str, ...]


def parse_date(text: str) -> date | None:
    """ISO dates, and day-first dates as Indian offices write them. Never month-first."""
    for form in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, form).date()
        except ValueError:
            continue
    return None


def _decimal(text: str, name: str, problems: list[str]) -> Decimal | None:
    try:
        number = Decimal(text.replace(",", ""))
    except InvalidOperation:
        problems.append(f"{name} {text!r} is not a number")
        return None
    if not number.is_finite():
        problems.append(f"{name} {text!r} is not a finite number")
        return None
    return number


def _status(text: str | None, problems: list[str]) -> FactStatus | None:
    if not text:
        problems.append("the status is missing")
        return None
    try:
        return FactStatus(text.strip().lower().replace(" ", "_").replace("-", "_"))
    except ValueError:
        problems.append(f"status {text!r} is not one of {STATUS_WORDS}")
        return None


def validate_facts(
    rows: list[RawRow], domain: Domain, departments: set[str], today: date
) -> tuple[list[FactRow], list[Reject]]:
    accepted: list[FactRow] = []
    rejects: list[Reject] = []
    seen: dict[tuple[str, str, str, str], str] = {}

    for row in rows:
        v = row.values
        problems: list[str] = []

        dept = (v.get("dept_code") or "").upper()
        if not dept:
            problems.append("the department is missing")
        elif dept not in departments:
            problems.append(f"unknown department {dept!r}")

        key = (v.get("metric_key") or "").lower()
        spec = CATALOGUE.get(key)
        if not key:
            problems.append("the metric is missing")
        elif spec is None:
            problems.append(f"unknown metric {key!r}")
        elif spec.domain is not domain:
            problems.append(
                f"metric {key} belongs to {spec.domain.value}, but this source is {domain.value}"
            )

        period = v.get("period_year") or ""
        if not PERIOD.match(period):
            problems.append(f"period {period!r} should look like 2025-26")
        sub = (v.get("period_sub") or "").upper()
        if sub not in SUB_PERIODS:
            problems.append(f"sub-period {sub!r} should be one of {', '.join(SUB_PERIODS)}")

        value = None
        if not v.get("value"):
            problems.append("the value is missing")
        else:
            value = _decimal(v["value"] or "", "value", problems)
            if value is not None and value < 0:
                problems.append(f"value {value} is negative")

        status = _status(v.get("status"), problems)

        as_of = None
        if not v.get("as_of"):
            problems.append("the as-of date is missing")
        else:
            as_of = parse_date(v["as_of"] or "")
            if as_of is None:
                problems.append(
                    f"as-of date {v['as_of']!r} is not a date (use 2026-09-21 or 21/09/2026)"
                )
            elif as_of > today:
                problems.append(f"as-of date {as_of} is in the future")

        numerator = denominator = None
        if v.get("numerator") or v.get("denominator"):
            if not (v.get("numerator") and v.get("denominator")):
                problems.append("a numerator needs a denominator, and the other way round")
            else:
                numerator = _decimal(v["numerator"] or "", "numerator", problems)
                denominator = _decimal(v["denominator"] or "", "denominator", problems)
                if denominator is not None and denominator < 0:
                    problems.append("the denominator is negative")

        unit = spec.unit if spec else ""
        if spec and v.get("unit") and v["unit"].strip().lower() != spec.unit.lower():
            problems.append(
                f"unit {v['unit']!r} does not match {spec.unit!r}, which this metric is counted in"
            )

        # a forecast must say so, or it could be added to actuals as if it were final (rule 4).
        # Provisional offers have no such rule: the contract only says they are kept separate,
        # and a closed year's provisional-offer count is legitimately final.
        if key == "fin.revenue_forecast" and status not in (None, FactStatus.FORECAST):
            problems.append("a revenue forecast must have the status forecast")

        slot = (dept, key, period, sub)
        if not problems and slot in seen:
            problems.append(f"duplicate of {seen[slot]}")

        if problems:
            rejects.append(Reject(row.ref, tuple(problems)))
            continue
        seen[slot] = row.ref
        assert value is not None and status is not None and as_of is not None
        accepted.append(
            FactRow(
                ref=row.ref, dept_code=dept, metric_key=key, period_year=period, period_sub=sub,
                value=value, numerator=numerator, denominator=denominator, unit=unit,
                status=status, as_of=as_of, source_ref=v.get("source_ref") or row.ref,
            )
        )  # fmt: skip
    return accepted, rejects


def validate_publications(
    rows: list[RawRow], departments: set[str]
) -> tuple[list[PublicationRow], list[Reject]]:
    accepted: list[PublicationRow] = []
    rejects: list[Reject] = []
    for row in rows:
        v = row.values
        problems: list[str] = []
        dedup = (v.get("dedup_key") or "").strip().lower()
        if not dedup:
            problems.append(
                "the DOI or internal id is missing, so a shared paper cannot be counted once"
            )
        if not v.get("title"):
            problems.append("the title is missing")
        period = v.get("period_year") or ""
        if not PERIOD.match(period):
            problems.append(f"period {period!r} should look like 2025-26")
        status = _status(v.get("status"), problems)
        codes = tuple(
            dict.fromkeys(
                c.strip().upper() for c in re.split(r"[;,]", v.get("dept_codes") or "") if c.strip()
            )
        )
        if not codes:
            problems.append("no department is credited")
        unknown = [c for c in codes if c not in departments]
        if unknown:
            problems.append(f"unknown department {', '.join(unknown)}")
        if problems:
            rejects.append(Reject(row.ref, tuple(problems)))
            continue
        assert status is not None
        accepted.append(
            PublicationRow(
                ref=row.ref, dedup_key=dedup, title=v["title"] or "", venue=v.get("venue") or "",
                period_year=period, indexing=v.get("indexing") or "", status=status, dept_codes=codes,
            )
        )  # fmt: skip
    return accepted, rejects
