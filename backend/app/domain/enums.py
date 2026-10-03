"""Enumerations shared by the engine, the graph and the API. Mirrors docs/DATA_CONTRACT.md."""

from enum import StrEnum


class Domain(StrEnum):
    ACADEMIC = "academic"
    RESEARCH = "research"
    PLACEMENT = "placement"
    FINANCE = "finance"
    REFERENCE = "reference"


class FactStatus(StrEnum):
    FINAL = "final"
    AUDITED = "audited"
    PROVISIONAL = "provisional"
    FORECAST = "forecast"
    PENDING_RECONCILIATION = "pending_reconciliation"


# Only these may be counted as actuals. Provisional, forecast and unreconciled figures are
# never shown or summed as final (rules 3 and 4).
ACTUAL_STATUSES = frozenset({FactStatus.FINAL, FactStatus.AUDITED})


class KpiFramework(StrEnum):
    NIRF = "NIRF"
    NAAC = "NAAC"
    STRATEGIC = "STRATEGIC"


class KpiStatus(StrEnum):
    MET = "met"
    AT_RISK = "at_risk"
    MISSED = "missed"
    UNDEFINED = "undefined"


class PeriodAgg(StrEnum):
    """How sub-periods (semesters, quarters) combine into a year for one metric (decision D14)."""

    SUM = "sum"
    LATEST = "latest"


class Role(StrEnum):
    REGISTRAR = "registrar"
    PRINCIPAL = "principal"  # Principal or Director
    DEAN = "dean"
    HOD = "hod"
    VIEWER = "viewer"  # Governing Council
    ADMIN = "admin"


class BriefStatus(StrEnum):
    DRAFT = "draft"
    ESCALATED = "escalated"  # validation could not be satisfied within the retry budget
    APPROVED = "approved"
    PUBLISHED = "published"
    ROLLED_BACK = "rolled_back"
    OVERRIDDEN = "overridden"
    RETURNED = "returned"  # sent back by the approver
