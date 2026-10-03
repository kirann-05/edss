"""The metric catalogue: stable keys that adapters map source columns onto.

Mirrors docs/DATA_CONTRACT.md section 3. `period_agg` is decision D14: it says how the
semesters or quarters of one year combine into a single figure for a department.

  sum     flows (students appeared, expenditure): add the sub-periods
  latest  snapshots (faculty count, budget, package statistics): take the last sub-period
"""

from app.domain.enums import Domain, PeriodAgg
from app.domain.models import MetricSpec

S, L = PeriodAgg.SUM, PeriodAgg.LATEST
A, R, P, F, X = (
    Domain.ACADEMIC,
    Domain.RESEARCH,
    Domain.PLACEMENT,
    Domain.FINANCE,
    Domain.REFERENCE,
)

_SPECS: tuple[MetricSpec, ...] = (
    # academic
    MetricSpec(
        key="acad.students_appeared",
        domain=A,
        label="Students appeared",
        unit="students",
        period_agg=S,
    ),
    MetricSpec(
        key="acad.students_passed", domain=A, label="Students passed", unit="students", period_agg=S
    ),
    MetricSpec(
        key="acad.co_attainment", domain=A, label="CO attainment level", unit="level", period_agg=L
    ),
    MetricSpec(
        key="acad.po_attainment", domain=A, label="PO attainment level", unit="level", period_agg=L
    ),
    MetricSpec(
        key="acad.courses_total", domain=A, label="Courses offered", unit="courses", period_agg=L
    ),
    MetricSpec(
        key="acad.courses_approved_syllabus",
        domain=A,
        label="Courses with approved syllabus",
        unit="courses",
        period_agg=L,
    ),
    MetricSpec(
        key="acad.courses_current_revision",
        domain=A,
        label="Courses on current revision",
        unit="courses",
        period_agg=L,
    ),
    MetricSpec(
        key="acad.courses_outcome_mapped",
        domain=A,
        label="Courses with outcome mapping",
        unit="courses",
        period_agg=L,
    ),
    # research
    MetricSpec(
        key="res.publications_count",
        domain=R,
        label="Publications (department credit)",
        unit="publications",
        period_agg=S,
    ),
    MetricSpec(
        key="res.citations_count", domain=R, label="Citations", unit="citations", period_agg=L
    ),
    MetricSpec(
        key="res.grant_sanctioned",
        domain=R,
        label="Research grant sanctioned",
        unit="INR lakh",
        period_agg=S,
    ),
    MetricSpec(
        key="res.grant_count", domain=R, label="Grants sanctioned", unit="grants", period_agg=S
    ),
    # placement
    MetricSpec(
        key="plc.eligible", domain=P, label="Students eligible", unit="students", period_agg=S
    ),
    MetricSpec(
        key="plc.registered", domain=P, label="Students registered", unit="students", period_agg=S
    ),
    MetricSpec(
        key="plc.placed_confirmed",
        domain=P,
        label="Placed, verified by Placement Cell",
        unit="students",
        period_agg=S,
    ),
    MetricSpec(
        key="plc.offers_provisional",
        domain=P,
        label="Offers not yet confirmed",
        unit="offers",
        period_agg=S,
    ),
    MetricSpec(
        key="plc.package_avg_lpa", domain=P, label="Average package", unit="LPA", period_agg=L
    ),
    MetricSpec(
        key="plc.package_median_lpa", domain=P, label="Median package", unit="LPA", period_agg=L
    ),
    MetricSpec(
        key="plc.package_max_lpa", domain=P, label="Highest package", unit="LPA", period_agg=L
    ),
    MetricSpec(
        key="plc.intern_required",
        domain=P,
        label="Internships required",
        unit="students",
        period_agg=S,
    ),
    MetricSpec(
        key="plc.intern_completed",
        domain=P,
        label="Internships completed",
        unit="students",
        period_agg=S,
    ),
    # finance
    MetricSpec(
        key="fin.budget_sanctioned",
        domain=F,
        label="Budget sanctioned (annual)",
        unit="INR lakh",
        period_agg=L,
    ),
    MetricSpec(
        key="fin.expenditure_actual",
        domain=F,
        label="Expenditure (actual)",
        unit="INR lakh",
        period_agg=S,
    ),
    MetricSpec(
        key="fin.revenue_actual", domain=F, label="Revenue (actual)", unit="INR lakh", period_agg=S
    ),
    MetricSpec(
        key="fin.revenue_forecast",
        domain=F,
        label="Revenue (forecast)",
        unit="INR lakh",
        period_agg=S,
    ),
    MetricSpec(
        key="fin.grant_received", domain=F, label="Grant received", unit="INR lakh", period_agg=S
    ),
    MetricSpec(
        key="fin.grant_utilized", domain=F, label="Grant utilised", unit="INR lakh", period_agg=S
    ),
    # reference denominators
    MetricSpec(key="ref.faculty_count", domain=X, label="Faculty", unit="faculty", period_agg=L),
    MetricSpec(
        key="ref.enrolled_students",
        domain=X,
        label="Enrolled students",
        unit="students",
        period_agg=L,
    ),
    MetricSpec(
        key="ref.sanctioned_intake", domain=X, label="Sanctioned intake", unit="seats", period_agg=L
    ),
)

CATALOGUE: dict[str, MetricSpec] = {spec.key: spec for spec in _SPECS}

# Order of sub-periods inside a year, used to find the latest one. AY and FY are whole-year
# records, so they have no siblings to order against.
SUB_PERIOD_ORDER: dict[str, int] = {
    "AY": 0,
    "FY": 0,
    "S1": 1,
    "S2": 2,
    "Q1": 1,
    "Q2": 2,
    "Q3": 3,
    "Q4": 4,
}

assert len(CATALOGUE) == len(_SPECS), "duplicate metric key in the catalogue"
