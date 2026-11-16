"""
STUB / PLACEHOLDER institutional data.
=======================================

This module stands in for the real department systems (academic ERP,
research office, placement cell, finance office). It exists so the
Executive Decision Support System can be run and demoed end-to-end
without any real integration wired up yet.

Swap this out later for a real connector backend (a database, CSV/Excel
exports, or live APIs) behind the SAME interface defined in
`eds/connector.py` -- no agent code should need to change when you do.

Every record below is clearly fictional / illustrative.
"""

from __future__ import annotations
import datetime as _dt

RUN_DATE = _dt.date.today().isoformat()

# ---------------------------------------------------------------------------
# Academic domain (per department)
# ---------------------------------------------------------------------------
ACADEMIC_RECORDS = [
    {
        "department": "Computer Science",
        "pass_percentage": 91.2,
        "co_po_attainment": 0.78,
        "curriculum_compliance": 0.96,
        "source_system": "Academic ERP - CS",
        "last_updated": RUN_DATE,
        "data_quality": "current",
    },
    {
        "department": "Electronics & Communication",
        "pass_percentage": 88.4,
        "co_po_attainment": 0.74,
        "curriculum_compliance": 0.93,
        "source_system": "Academic ERP - ECE",
        "last_updated": RUN_DATE,
        "data_quality": "current",
    },
    {
        "department": "Mechanical Engineering",
        "pass_percentage": 85.7,
        "co_po_attainment": 0.71,
        "curriculum_compliance": 0.90,
        "source_system": "Academic ERP - MECH",
        "last_updated": RUN_DATE,
        "data_quality": "current",
    },
    {
        "department": "Civil Engineering",
        "pass_percentage": 83.1,
        "co_po_attainment": 0.69,
        "curriculum_compliance": 0.88,
        "source_system": "Academic ERP - CIVIL",
        "last_updated": "2026-08-02",
        "data_quality": "stale",  # flagged: > 30 days old
    },
]

# ---------------------------------------------------------------------------
# Research domain (per department)
# ---------------------------------------------------------------------------
RESEARCH_RECORDS = [
    {
        "department": "Computer Science",
        "publications": 42,
        "citations": 310,
        "grants_secured_lakhs": 85.0,
        "collaboration_ids": ["CS-ECE-2026-01"],
        "source_system": "Research Office Registry",
        "last_updated": RUN_DATE,
    },
    {
        "department": "Electronics & Communication",
        "publications": 27,
        "citations": 190,
        "grants_secured_lakhs": 40.0,
        "collaboration_ids": ["CS-ECE-2026-01"],  # same collab as CS -> must not double count
        "source_system": "Research Office Registry",
        "last_updated": RUN_DATE,
    },
    {
        "department": "Mechanical Engineering",
        "publications": 19,
        "citations": 88,
        "grants_secured_lakhs": 22.5,
        "collaboration_ids": [],
        "source_system": "Research Office Registry",
        "last_updated": RUN_DATE,
    },
    {
        "department": "Civil Engineering",
        "publications": 14,
        "citations": 51,
        "grants_secured_lakhs": 12.0,
        "collaboration_ids": [],
        "source_system": "Research Office Registry",
        "last_updated": RUN_DATE,
    },
]

# ---------------------------------------------------------------------------
# Placement domain (per department)
# ---------------------------------------------------------------------------
PLACEMENT_RECORDS = [
    {
        "department": "Computer Science",
        "eligible_students": 180,
        "placed_students": 162,
        "average_package_lakhs": 8.4,
        "internship_completion_pct": 94.0,
        "provisional_offers": 6,  # not yet confirmed - must not be counted as placed
        "source_system": "Placement Cell CRM",
        "verified": True,
    },
    {
        "department": "Electronics & Communication",
        "eligible_students": 140,
        "placed_students": 109,
        "average_package_lakhs": 6.1,
        "internship_completion_pct": 89.0,
        "provisional_offers": 4,
        "source_system": "Placement Cell CRM",
        "verified": True,
    },
    {
        "department": "Mechanical Engineering",
        "eligible_students": 120,
        "placed_students": 78,
        "average_package_lakhs": 5.2,
        "internship_completion_pct": 81.0,
        "provisional_offers": 3,
        "source_system": "Placement Cell CRM",
        "verified": True,
    },
    {
        "department": "Civil Engineering",
        "eligible_students": 95,
        "placed_students": 51,
        "average_package_lakhs": 4.6,
        "internship_completion_pct": 76.0,
        "provisional_offers": 2,
        "source_system": "Placement Cell CRM",
        "verified": False,  # incomplete reporting -> must be flagged
    },
]

# ---------------------------------------------------------------------------
# Finance domain (institution-level, not per department)
# ---------------------------------------------------------------------------
FINANCE_RECORD = {
    "budget_allocated_lakhs": 1200.0,
    "budget_utilized_lakhs": 947.0,
    "revenue_lakhs": 1510.0,
    "grant_funds_received_lakhs": 159.5,
    "grant_funds_spent_lakhs": 121.0,
    "pending_reconciliation_lakhs": 18.0,  # flagged: not yet finance-office reconciled
    "source_system": "Finance ERP (Audited Ledger)",
    "reconciled": True,
    "as_of": RUN_DATE,
}

# ---------------------------------------------------------------------------
# Approved KPI definitions and strategic-plan / NIRF-NAAC targets
# ---------------------------------------------------------------------------
KPI_DEFINITIONS = {
    "institution_pass_percentage": {
        "formula": "mean(department.pass_percentage, weighted by eligible cohort)",
        "target": 90.0,
        "framework": "NAAC Criterion 2",
        "unit": "%",
    },
    "institution_co_po_attainment": {
        "formula": "mean(department.co_po_attainment)",
        "target": 0.75,
        "framework": "NAAC Criterion 2",
        "unit": "ratio",
    },
    "institution_publications_per_faculty": {
        "formula": "sum(department.publications, de-duplicated by collaboration_id) / total_faculty_count",
        "target": 1.2,
        "framework": "NIRF Research & Professional Practice (RP)",
        "unit": "count",
    },
    "institution_placement_percentage": {
        "formula": "sum(placed_students, confirmed only) / sum(eligible_students)",
        "target": 85.0,
        "framework": "NIRF Graduation Outcomes (GO)",
        "unit": "%",
    },
    "institution_average_package": {
        "formula": "weighted_mean(average_package_lakhs, weighted by placed_students)",
        "target": 6.5,
        "framework": "NIRF Graduation Outcomes (GO)",
        "unit": "INR lakhs",
    },
    "institution_budget_utilization": {
        "formula": "budget_utilized_lakhs / budget_allocated_lakhs",
        "target": 0.90,
        "framework": "Strategic Plan FY26",
        "unit": "ratio",
    },
}

# Total faculty count, used by the publications-per-faculty KPI.
TOTAL_FACULTY_COUNT = 96

# Assumed total student cohort size, used only for narrative context (not a KPI input).
TOTAL_STUDENT_COUNT = 2150
