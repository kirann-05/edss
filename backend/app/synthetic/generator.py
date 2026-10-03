"""Deterministic synthetic dataset for the demo and the tests (docs/DATA_CONTRACT.md section 6).

Eight departments, three academic years, seed 42. It plants ten traps on purpose, each with a
test that asserts the system handles it (tests/synthetic/test_traps.py):

  T1  CIVIL placement data is 150 days old                      flagged stale
  T2  MECH has no research record for the latest year           flagged missing, not zero
  T3  about 12 percent of placement offers are provisional      kept apart, never counted
  T4  the open finance quarter has revenue forecast rows        never summed into actuals
  T5  CSE and ECE share one DOI                                 counted once for the institution
  T6  placement is exactly 74.96 percent against a target of 75 missed, shown to one place as 75.0
  T7  department pass rates average higher than the weighted    institution uses totals
  T8  one BIOTECH expenditure figure is pending reconciliation  badged and kept out of actuals
  T9  AIML has no graduating batch, so every placement ratio    undefined, not 0 or 100
      has a zero denominator
  T10 two KPIs miss, one is at risk, the rest are met

Periods are labels. The generator stamps every as_of date relative to `reference_date` so the
demo is "current" on the day it is seeded. Closed years carry only data that was final by then.
"""

import hashlib
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.enums import Domain, FactStatus
from app.domain.models import (
    Department,
    IngestBatch,
    MetricFact,
    Publication,
    SourceSystem,
)
from app.kpi.catalogue import CATALOGUE

CURRENT_PERIOD = "2025-26"
SHARED_DOI = "doi:10.5555/edss.2025.shared"  # trap T5, credited to CSE and ECE

DEPARTMENTS: tuple[Department, ...] = (
    Department(code="CSE", name="Computer Science and Engineering", school="School of Computer Science and Engineering"),
    Department(code="AIML", name="Artificial Intelligence and Machine Learning", school="School of Computer Science and Engineering"),
    Department(code="MCA", name="Computer Applications", school="School of Computer Science and Engineering"),
    Department(code="ECE", name="Electronics and Communication Engineering", school="School of Electronics and Electrical"),
    Department(code="EEE", name="Electrical and Electronics Engineering", school="School of Electronics and Electrical"),
    Department(code="MECH", name="Mechanical Engineering", school="School of Mechanical and Civil"),
    Department(code="CIVIL", name="Civil Engineering", school="School of Mechanical and Civil"),
    Department(code="BIOTECH", name="Biotechnology", school="School of Biosciences"),
)  # fmt: skip
CODES = tuple(d.code for d in DEPARTMENTS)

SOURCES: dict[Domain, SourceSystem] = {
    Domain.ACADEMIC: SourceSystem(id=1, name="Examination Section results export", owner_office="Controller of Examinations", kind="csv"),
    Domain.RESEARCH: SourceSystem(id=2, name="R&D Cell publication register", owner_office="Research and Development Cell", kind="csv"),
    Domain.PLACEMENT: SourceSystem(id=3, name="Placement Cell offers view", owner_office="Training and Placement Cell", kind="sql"),
    Domain.FINANCE: SourceSystem(id=4, name="Accounts Office quarterly statements", owner_office="Accounts Office", kind="csv"),
    Domain.REFERENCE: SourceSystem(id=5, name="HR and Admissions registers", owner_office="Registrar's Office", kind="csv"),
}  # fmt: skip
_FILES = {
    Domain.ACADEMIC: "academic_results_{period}.csv",
    Domain.RESEARCH: "research_register_{period}.csv",
    Domain.PLACEMENT: "v_placement_summary",
    Domain.FINANCE: "finance_statements_{period}.csv",
    Domain.REFERENCE: "reference_counts_{period}.csv",
}

# Age in days of the newest record of each domain in the current period
_FRESHNESS = {
    Domain.ACADEMIC: 24,
    Domain.RESEARCH: 41,
    Domain.PLACEMENT: 18,
    Domain.FINANCE: 12,
    Domain.REFERENCE: 30,
}
_STALE_PLACEMENT_DAYS = 150  # trap T1

FACULTY = {
    "CSE": 64,
    "AIML": 36,
    "MCA": 24,
    "ECE": 52,
    "EEE": 44,
    "MECH": 58,
    "CIVIL": 40,
    "BIOTECH": 32,
}
ENROLLED = {
    "CSE": 905,
    "AIML": 330,
    "MCA": 118,
    "ECE": 690,
    "EEE": 450,
    "MECH": 700,
    "CIVIL": 440,
    "BIOTECH": 210,
}
INTAKE = {"CSE": 240, "AIML": 120, "MCA": 60, "ECE": 180, "EEE": 120, "MECH": 180, "CIVIL": 120, "BIOTECH": 60}  # fmt: skip


@dataclass(frozen=True)
class Year:
    period: str
    pass_pts: float  # added to every department's pass rate, percentage points
    place_pts: float
    pubs: float  # multiplier on publication volume
    money: float  # multiplier on finance volume
    people: float  # multiplier on headcounts
    quality: float  # offset on attainment levels
    age_days: int  # how old a closed year's records are
    current: bool = False


YEARS: tuple[Year, ...] = (
    Year("2023-24", -3.0, -7.0, 0.80, 0.86, 0.94, -0.10, 760),
    Year("2024-25", -1.4, -3.5, 0.90, 0.93, 0.97, -0.05, 395),
    Year(CURRENT_PERIOD, 0.0, 0.0, 1.00, 1.00, 1.00, 0.0, 0, current=True),
)

# --- academic -----------------------------------------------------------------------------
APPEARED_TOTAL = 9200  # student-semester exam attendances, current year, S1 plus S2
PASSED_TOTAL = 7940  # 86.30 percent, inside the 2 percent band above the 85 target (at risk)
# Small departments pass more often than large ones, so the simple mean of department
# rates (about 89.4) is well above the weighted institution rate (trap T7)
PASS_RATE = {"CSE": 0.84, "AIML": 0.95, "MCA": 0.97, "ECE": 0.85, "EEE": 0.88, "MECH": 0.80, "CIVIL": 0.90, "BIOTECH": 0.96}  # fmt: skip
COURSES = {
    "CSE": 38,
    "AIML": 24,
    "MCA": 20,
    "ECE": 36,
    "EEE": 32,
    "MECH": 34,
    "CIVIL": 30,
    "BIOTECH": 26,
}
COURSES_CURRENT_REVISION = {"CSE": 36, "AIML": 24, "MCA": 18, "ECE": 34, "EEE": 30, "MECH": 30, "CIVIL": 28, "BIOTECH": 24}  # fmt: skip
CO_LEVEL = {"CSE": "2.70", "AIML": "2.60", "MCA": "2.80", "ECE": "2.55", "EEE": "2.60", "MECH": "2.55", "CIVIL": "2.70", "BIOTECH": "2.75"}  # fmt: skip
PO_LEVEL = {"CSE": "2.50", "AIML": "2.45", "MCA": "2.60", "ECE": "2.40", "EEE": "2.50", "MECH": "2.40", "CIVIL": "2.55", "BIOTECH": "2.60"}  # fmt: skip

# --- research -----------------------------------------------------------------------------
# Department credit per year. MECH has no record at all in the current year (trap T2)
PUB_CREDITS = {"CSE": 88, "AIML": 40, "MCA": 10, "ECE": 60, "EEE": 38, "MECH": 36, "CIVIL": 26, "BIOTECH": 30}  # fmt: skip
# Papers shared by two departments: (lead, partner, count). The first CSE and ECE paper carries
# the shared DOI (trap T5)
PUB_PAIRS = (("CSE", "AIML", 8), ("CSE", "ECE", 5), ("ECE", "EEE", 4), ("BIOTECH", "CIVIL", 2), ("AIML", "MCA", 1))  # fmt: skip
CITATIONS_PER_LED_PAPER = {"CSE": 5.0, "AIML": 3.6, "MCA": 2.4, "ECE": 4.4, "EEE": 3.9, "MECH": 3.2, "CIVIL": 3.5, "BIOTECH": 5.4}  # fmt: skip
GRANT_LAKH = {"CSE": 560, "AIML": 180, "MCA": 25, "ECE": 410, "EEE": 260, "MECH": 150, "CIVIL": 190, "BIOTECH": 260}  # fmt: skip

# --- placement ----------------------------------------------------------------------------
REGISTERED_TOTAL = 1250
PLACED_TOTAL = 937  # exactly 74.96 percent of 1250 (trap T6)
PROVISIONAL_SHARE = 0.12  # of all offers (trap T3)
REGISTERED_WEIGHT = {"CSE": 240, "MCA": 60, "ECE": 180, "EEE": 120, "MECH": 180, "CIVIL": 120, "BIOTECH": 60}  # fmt: skip
PLACE_RATE = {"CSE": 0.80, "MCA": 0.78, "ECE": 0.74, "EEE": 0.72, "MECH": 0.68, "CIVIL": 0.66, "BIOTECH": 0.82}  # fmt: skip
PACKAGE_LPA = {
    "CSE": 7.8,
    "MCA": 6.0,
    "ECE": 6.4,
    "EEE": 5.8,
    "MECH": 5.2,
    "CIVIL": 4.9,
    "BIOTECH": 5.5,
}
INTERN_RATE = {"CSE": 0.88, "MCA": 0.85, "ECE": 0.84, "EEE": 0.83, "MECH": 0.82, "CIVIL": 0.80, "BIOTECH": 0.86}  # fmt: skip
NO_GRADUATING_BATCH = "AIML"  # trap T9: every placement ratio has a zero denominator

# --- finance (INR lakh) -------------------------------------------------------------------
BUDGET = {"CSE": 620, "AIML": 300, "MCA": 150, "ECE": 520, "EEE": 400, "MECH": 560, "CIVIL": 380, "BIOTECH": 320}  # fmt: skip
SPEND_RATE_YTD = {"CSE": 0.78, "AIML": 0.74, "MCA": 0.70, "ECE": 0.79, "EEE": 0.76, "MECH": 0.77, "CIVIL": 0.73, "BIOTECH": 0.72}  # fmt: skip
SPEND_BY_QUARTER = (0.28, 0.36, 0.36)
REVENUE_SHARE_OF_BUDGET = 0.90  # annual, split evenly over the quarters
GRANT_RECEIVED_YTD = {"CSE": 300, "AIML": 100, "MCA": 15, "ECE": 220, "EEE": 140, "MECH": 120, "CIVIL": 100, "BIOTECH": 140}  # fmt: skip
GRANT_UTILISATION = {"CSE": 0.88, "AIML": 0.84, "MCA": 0.80, "ECE": 0.86, "EEE": 0.85, "MECH": 0.83, "CIVIL": 0.87, "BIOTECH": 0.90}  # fmt: skip
PENDING_RECONCILIATION = ("BIOTECH", "fin.expenditure_actual", "Q3")  # trap T8
# Finance history is kept through Q3 so year-to-date trends compare like with like
QUARTERS = ("Q1", "Q2", "Q3")


@dataclass(frozen=True)
class SyntheticDataset:
    reference_date: date
    current_period: str
    periods: tuple[str, ...]
    departments: tuple[Department, ...]
    source_systems: tuple[SourceSystem, ...]
    batches: tuple[IngestBatch, ...]
    facts: tuple[MetricFact, ...]
    publications: tuple[Publication, ...]


def split_total(total: int, weights: Sequence[float]) -> list[int]:
    """Integer parts proportional to weights that sum exactly to total (largest remainder)."""
    weight_sum = sum(weights)
    if total == 0 or weight_sum == 0:
        return [0] * len(weights)
    quotas = [total * w / weight_sum for w in weights]
    parts = [int(q) for q in quotas]
    by_remainder = sorted(range(len(weights)), key=lambda i: (-(quotas[i] - parts[i]), i))
    for i in by_remainder[: total - sum(parts)]:
        parts[i] += 1
    return parts


def nudge_to_total(
    values: Sequence[int], total: int, order: Sequence[int], cap: Sequence[int] | None = None
) -> list[int]:
    """Add or remove single units, round-robin along `order`, until the values sum to total."""
    result = list(values)
    difference = total - sum(result)
    step = 1 if difference > 0 else -1
    attempts, limit = 0, (abs(difference) + 1) * len(order) + 1
    while difference != 0:
        attempts += 1
        if attempts > limit:
            raise ValueError("cannot reach the requested total within the caps")
        index = order[attempts % len(order)]
        candidate = result[index] + step
        if candidate >= 0 and (cap is None or candidate <= cap[index]):
            result[index] = candidate
            difference -= step
    return result


class _Builder:
    def __init__(self, reference_date: date) -> None:
        self.reference_date = reference_date
        self.facts: list[MetricFact] = []
        self._batch_ids: dict[tuple[Domain, str], int] = {}
        self._rows: dict[tuple[Domain, str], int] = {}
        self._newest: dict[tuple[Domain, str], date] = {}

    def add(
        self,
        key: str,
        dept: str,
        period: str,
        sub: str,
        value: int | float | str | Decimal,
        as_of: date,
        status: FactStatus = FactStatus.FINAL,
    ) -> None:
        spec = CATALOGUE[key]
        slot = (spec.domain, period)
        batch_id = self._batch_ids.setdefault(slot, len(self._batch_ids) + 1)
        row = self._rows[slot] = self._rows.get(slot, 0) + 1
        self._newest[slot] = max(self._newest.get(slot, as_of), as_of)
        source = SOURCES[spec.domain]
        file_ref = _FILES[spec.domain].format(period=period)
        source_ref = (
            f"sql:{file_ref}:{dept}/{period}/{key}"
            if source.kind == "sql"
            else f"{file_ref}:row {row}"
        )
        self.facts.append(
            MetricFact(
                id=len(self.facts) + 1,
                batch_id=batch_id,
                domain=spec.domain,
                metric_key=key,
                dept_code=dept,
                period_year=period,
                period_sub=sub,
                value=Decimal(str(value)),
                unit=spec.unit,
                status=status,
                as_of=as_of,
                source_system_id=source.id,
                source_ref=source_ref,
            )
        )

    def batches(self) -> tuple[IngestBatch, ...]:
        batches = []
        for (domain, period), batch_id in sorted(self._batch_ids.items(), key=lambda kv: kv[1]):
            rows = self._rows[(domain, period)]
            file_ref = _FILES[domain].format(period=period)
            digest = hashlib.sha256(f"{file_ref}:{rows}".encode()).hexdigest()[:16]
            batches.append(
                IngestBatch(
                    id=batch_id,
                    source_system_id=SOURCES[domain].id,
                    data_mode="synthetic",
                    domain=domain,
                    row_count=rows,
                    file_ref=file_ref,
                    checksum=digest,
                    ingested_by="synthetic-generator",
                    finished_at=self._newest[(domain, period)],
                )
            )
        return tuple(batches)


def _as_of(year: Year, domain: Domain, reference: date) -> date:
    days = _FRESHNESS[domain] if year.current else year.age_days
    return reference - timedelta(days=days)


def _scaled(value: float, factor: float) -> int:
    return round(value * factor)


def _academic(b: _Builder, year: Year) -> None:
    as_of = _as_of(year, Domain.ACADEMIC, b.reference_date)
    weights = [ENROLLED[c] for c in CODES]
    appeared_total = _scaled(APPEARED_TOTAL, year.people)
    s1_total = round(appeared_total * 0.511)
    appeared_s1 = split_total(s1_total, weights)
    appeared_s2 = split_total(appeared_total - s1_total, weights)

    rates = [PASS_RATE[c] + year.pass_pts / 100 for c in CODES]
    passed = [
        round((a1 + a2) * r) for a1, a2, r in zip(appeared_s1, appeared_s2, rates, strict=True)
    ]
    if year.current:
        biggest_first = sorted(range(len(CODES)), key=lambda i: -(appeared_s1[i] + appeared_s2[i]))
        passed = nudge_to_total(
            passed, PASSED_TOTAL, biggest_first,
            cap=[a1 + a2 for a1, a2 in zip(appeared_s1, appeared_s2, strict=True)],
        )  # fmt: skip

    for i, code in enumerate(CODES):
        s1_share = appeared_s1[i] / (appeared_s1[i] + appeared_s2[i])
        passed_s1 = round(passed[i] * s1_share)
        for sub, appeared_n, passed_n in (
            ("S1", appeared_s1[i], passed_s1),
            ("S2", appeared_s2[i], passed[i] - passed_s1),
        ):
            b.add("acad.students_appeared", code, year.period, sub, appeared_n, as_of)
            b.add("acad.students_passed", code, year.period, sub, passed_n, as_of)

        # Courses: S1 is a little behind S2, and revisions only ever move forward
        total_s2 = COURSES[code]
        revised_factor = 1.0 if year.current else (0.93 if year.period == "2024-25" else 0.90)
        revised_s2 = _scaled(COURSES_CURRENT_REVISION[code], revised_factor)
        for sub, total_n, revised_n, lag in (("S1", total_s2 - 1, revised_s2 - 2, 1), ("S2", total_s2, revised_s2, 0)):  # fmt: skip
            b.add("acad.courses_total", code, year.period, sub, total_n, as_of)
            b.add("acad.courses_current_revision", code, year.period, sub, max(revised_n, 0), as_of)
            b.add("acad.courses_approved_syllabus", code, year.period, sub, total_n - lag, as_of)
            b.add("acad.courses_outcome_mapped", code, year.period, sub, total_n - 1 - lag, as_of)
        b.add(
            "acad.co_attainment",
            code,
            year.period,
            "AY",
            _level(CO_LEVEL[code], year.quality),
            as_of,
        )
        b.add(
            "acad.po_attainment",
            code,
            year.period,
            "AY",
            _level(PO_LEVEL[code], year.quality),
            as_of,
        )


def _level(base: str, offset: float) -> Decimal:
    return (Decimal(base) + Decimal(str(offset))).quantize(Decimal("0.01"))


def _research(b: _Builder, year: Year, rng: random.Random) -> list[Publication]:
    as_of = _as_of(year, Domain.RESEARCH, b.reference_date)
    has_record = [c for c in CODES if not (year.current and c == "MECH")]  # trap T2

    credit = {c: _scaled(PUB_CREDITS[c], year.pubs) for c in has_record}
    pairs = [
        (lead, partner, max(1, _scaled(n, year.pubs)))
        for lead, partner, n in PUB_PAIRS
        if lead in credit and partner in credit
    ]
    shared_by = {
        c: sum(n for lead, partner, n in pairs if c in (lead, partner)) for c in has_record
    }
    solo = {c: credit[c] - shared_by[c] for c in has_record}
    assert all(n >= 0 for n in solo.values()), "department credit smaller than its shared papers"

    topics = ["graph learning", "edge inference", "power electronics", "structural health", "protein folding",
              "wireless sensing", "supply chains", "clean energy", "federated analytics", "soil mechanics"]  # fmt: skip
    venues = [
        "IEEE Access",
        "Elsevier Procedia",
        "Springer LNCS",
        "ACM Digital Library",
        "Scientific Reports",
    ]
    year4 = year.period[:4]
    papers: list[Publication] = []
    shared_doi_assigned = False

    def paper(depts: tuple[str, ...], key: str | None = None) -> None:
        number = len(papers) + 1
        papers.append(
            Publication(
                id=0,  # numbered by the caller across years
                batch_id=0,
                dedup_key=key or f"doi:10.5555/edss.{year4}.{number:04d}",
                title=f"{rng.choice(topics).capitalize()} study {number}",
                venue=rng.choice(venues),
                period_year=year.period,
                indexing=rng.choice(["Scopus", "Web of Science", "UGC CARE"]),
                status=FactStatus.FINAL,
                dept_codes=depts,
            )
        )

    for lead, partner, n in pairs:
        for _ in range(n):
            planted = year.current and {lead, partner} == {"CSE", "ECE"} and not shared_doi_assigned
            if planted:
                shared_doi_assigned = True
            paper((lead, partner), SHARED_DOI if planted else None)
    for code in has_record:
        for _ in range(solo[code]):
            paper((code,))

    led: dict[str, int] = {c: 0 for c in has_record}
    for p in papers:
        led[p.dept_codes[0]] += 1
    for code in has_record:
        b.add("res.publications_count", code, year.period, "AY", credit[code], as_of)
        b.add("res.citations_count", code, year.period, "AY",
              round(led[code] * CITATIONS_PER_LED_PAPER[code]), as_of)  # fmt: skip
        grant = _scaled(GRANT_LAKH[code], year.money)
        b.add("res.grant_sanctioned", code, year.period, "AY", grant, as_of)
        b.add("res.grant_count", code, year.period, "AY", max(1, round(grant / 45)), as_of)
    return papers


def _placement(b: _Builder, year: Year) -> None:
    codes = [c for c in CODES if c != NO_GRADUATING_BATCH]
    registered = dict(
        zip(
            codes,
            split_total(
                _scaled(REGISTERED_TOTAL, year.people), [REGISTERED_WEIGHT[c] for c in codes]
            ),
            strict=True,
        )
    )
    placed = [round(registered[c] * (PLACE_RATE[c] + year.place_pts / 100)) for c in codes]
    if year.current:
        largest_first = sorted(range(len(codes)), key=lambda i: -registered[codes[i]])
        placed = nudge_to_total(
            placed, PLACED_TOTAL, largest_first, cap=[registered[c] for c in codes]
        )
    placed_by = dict(zip(codes, placed, strict=True))

    base_as_of = _as_of(year, Domain.PLACEMENT, b.reference_date)
    package_growth = 1.0 if year.current else (0.93 if year.period == "2024-25" else 0.88)

    for code in CODES:
        as_of = base_as_of
        if year.current and code == "CIVIL":
            as_of = b.reference_date - timedelta(days=_STALE_PLACEMENT_DAYS)  # trap T1
        if code == NO_GRADUATING_BATCH:  # trap T9: recorded, with nothing to divide by
            for key in ("plc.eligible", "plc.registered", "plc.placed_confirmed", "plc.offers_provisional",
                        "plc.intern_required", "plc.intern_completed", "plc.package_avg_lpa",
                        "plc.package_median_lpa", "plc.package_max_lpa"):  # fmt: skip
                b.add(key, code, year.period, "AY", 0, as_of)
            continue

        reg, plc = registered[code], placed_by[code]
        eligible = math.ceil(reg / 0.90)
        provisional = (
            round(plc * PROVISIONAL_SHARE / (1 - PROVISIONAL_SHARE)) if year.current else 0
        )
        average = round(PACKAGE_LPA[code] * package_growth, 2)
        b.add("plc.eligible", code, year.period, "AY", eligible, as_of)
        b.add("plc.registered", code, year.period, "AY", reg, as_of)
        b.add("plc.placed_confirmed", code, year.period, "AY", plc, as_of)
        # trap T3: kept as its own metric with its own status, never part of a percentage
        b.add("plc.offers_provisional", code, year.period, "AY", provisional, as_of,
              FactStatus.PROVISIONAL if year.current else FactStatus.FINAL)  # fmt: skip
        b.add("plc.package_avg_lpa", code, year.period, "AY", average, as_of)
        b.add("plc.package_median_lpa", code, year.period, "AY", round(average * 0.85, 2), as_of)
        b.add("plc.package_max_lpa", code, year.period, "AY", round(average * 2.6, 2), as_of)
        b.add("plc.intern_required", code, year.period, "AY", eligible, as_of)
        b.add(
            "plc.intern_completed",
            code,
            year.period,
            "AY",
            round(eligible * INTERN_RATE[code]),
            as_of,
        )


def _finance(b: _Builder, year: Year) -> None:
    as_of = _as_of(year, Domain.FINANCE, b.reference_date)
    for code in CODES:
        budget = _scaled(BUDGET[code], year.money)
        b.add("fin.budget_sanctioned", code, year.period, "FY", budget, as_of)
        for q, quarter in enumerate(QUARTERS):
            audited = FactStatus.AUDITED if (not year.current or q < 2) else FactStatus.FINAL
            spend = round(budget * SPEND_RATE_YTD[code] * SPEND_BY_QUARTER[q])
            status = audited
            if year.current and (code, "fin.expenditure_actual", quarter) == PENDING_RECONCILIATION:
                status = FactStatus.PENDING_RECONCILIATION  # trap T8
            b.add("fin.expenditure_actual", code, year.period, quarter, spend, as_of, status)
            b.add("fin.revenue_actual", code, year.period, quarter,
                  round(budget * REVENUE_SHARE_OF_BUDGET / 4), as_of, audited)  # fmt: skip
            received = round(_scaled(GRANT_RECEIVED_YTD[code], year.money) / 3)
            b.add("fin.grant_received", code, year.period, quarter, received, as_of, audited)
            b.add("fin.grant_utilized", code, year.period, quarter,
                  round(received * GRANT_UTILISATION[code]), as_of, audited)  # fmt: skip
        if year.current:  # trap T4: the open quarter only has a forecast
            b.add("fin.revenue_forecast", code, year.period, "Q4",
                  round(budget * REVENUE_SHARE_OF_BUDGET / 4), as_of, FactStatus.FORECAST)  # fmt: skip


def _reference(b: _Builder, year: Year) -> None:
    as_of = _as_of(year, Domain.REFERENCE, b.reference_date)
    for code in CODES:
        b.add(
            "ref.faculty_count", code, year.period, "AY", _scaled(FACULTY[code], year.people), as_of
        )
        b.add(
            "ref.enrolled_students",
            code,
            year.period,
            "AY",
            _scaled(ENROLLED[code], year.people),
            as_of,
        )
        b.add("ref.sanctioned_intake", code, year.period, "AY", INTAKE[code], as_of)


def generate(reference_date: date, seed: int = 42) -> SyntheticDataset:
    """Build the whole dataset. Same seed and reference date always give the same data."""
    rng = random.Random(seed)
    builder = _Builder(reference_date)
    publications: list[Publication] = []
    for year in YEARS:
        _academic(builder, year)
        for paper in _research(builder, year, rng):
            publications.append(paper)
        _placement(builder, year)
        _finance(builder, year)
        _reference(builder, year)

    batches = builder.batches()
    research_batch = {b.file_ref: b.id for b in batches if b.domain is Domain.RESEARCH}
    numbered = [
        p.model_copy(
            update={
                "id": number,
                "batch_id": research_batch[_FILES[Domain.RESEARCH].format(period=p.period_year)],
            }
        )
        for number, p in enumerate(publications, start=1)
    ]
    return SyntheticDataset(
        reference_date=reference_date,
        current_period=CURRENT_PERIOD,
        periods=tuple(y.period for y in YEARS),
        departments=DEPARTMENTS,
        source_systems=tuple(SOURCES[d] for d in Domain),
        batches=batches,
        facts=tuple(builder.facts),
        publications=tuple(numbered),
    )
