"""
Lab 3 - Reusable, schema-typed skills: plan and format.

    skill plan(inputs) -> Plan:
        return expand(inputs).lock()
    skill format_decision(result, template) -> Document

A skill is case-agnostic: the same `plan_skill` and `format_decision_skill`
must work unchanged whether the request is "Q1 review cycle" or
"NAAC re-accreditation snapshot" -- only `inputs` changes.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Dict, List


DEFAULT_DOMAINS = ["academic", "research", "placement", "finance"]
DEFAULT_KPIS = [
    "institution_pass_percentage",
    "institution_co_po_attainment",
    "institution_publications_per_faculty",
    "institution_placement_percentage",
    "institution_average_package",
    "institution_budget_utilization",
]


@dataclass(frozen=True)
class Plan:
    """A locked specification the pipeline obeys. Immutable once created
    (Python dataclasses are 'locked' here by convention: nothing in this
    codebase mutates a Plan instance after `plan_skill` returns it)."""

    review_cycle: str
    domains: tuple
    kpis: tuple
    requested_by: str
    constraints: tuple
    created_at: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "review_cycle": self.review_cycle,
            "domains": list(self.domains),
            "kpis": list(self.kpis),
            "requested_by": self.requested_by,
            "constraints": list(self.constraints),
            "created_at": self.created_at,
        }


def plan_skill(inputs: Dict[str, Any]) -> Plan:
    """expand(inputs).lock() -- fill defaults, then freeze."""
    expanded = {
        "review_cycle": inputs.get("review_cycle", "unscheduled review"),
        "domains": tuple(inputs.get("domains", DEFAULT_DOMAINS)),
        "kpis": tuple(inputs.get("kpis", DEFAULT_KPIS)),
        "requested_by": inputs.get("requested_by", "unspecified requester"),
        "constraints": tuple(inputs.get(
            "constraints",
            [
                "human approval required before circulation",
                "no forecast or unreconciled figure presented as final",
                "every KPI must cite its formula and source",
                "drill-down evidence traceable to source department",
            ],
        )),
        "created_at": _dt.datetime.utcnow().isoformat(),
    }
    return Plan(**expanded)  # .lock() == returning an immutable dataclass


@dataclass
class Document:
    """A formatted, human-readable rendering of a decision-brief result."""

    title: str
    sections: List[Dict[str, Any]] = field(default_factory=list)

    def add_section(self, heading: str, body: Any) -> None:
        self.sections.append({"heading": heading, "body": body})

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", ""]
        for sec in self.sections:
            lines.append(f"## {sec['heading']}")
            body = sec["body"]
            if isinstance(body, str):
                lines.append(body)
            elif isinstance(body, list):
                for item in body:
                    lines.append(f"- {item}")
            elif isinstance(body, dict):
                for k, v in body.items():
                    lines.append(f"- **{k}**: {v}")
            lines.append("")
        return "\n".join(lines)


def format_decision_skill(result: Dict[str, Any], template: str = "executive_report") -> Document:
    """Render a decision-brief result into a Document. `template` is a
    label only in this reference implementation -- swap in real
    templates (per-institution letterhead, etc.) without touching
    callers."""
    doc = Document(title=result.get("title", "Executive Decision Brief"))
    for section in result.get("sections", []):
        doc.add_section(section["heading"], section["body"])
    return doc
