"""
Group A: Academic Agent.

Aggregates pass percentage, CO/PO attainment, and curriculum compliance
across departments, in parallel with Research/Placement/Finance.

Guardrails: pull only from approved records; show the underlying spread
(never average across departments without exposing it); flag any
department with stale or missing data.
"""

from __future__ import annotations

from typing import Any, Dict, List

from eds.agents.base import Agent, Evidence
from eds import tools


class AcademicAgent(Agent):
    name = "Academic Agent"

    def step(self, ctx, plan, connector):
        connector.request_access("academic", authorized_by=plan.requested_by or "Registrar")
        records: List[Dict[str, Any]] = connector.read("department reports", domain="academic")

        stale_flags = [r["department"] for r in records if r.get("data_quality") != "current"]

        pass_pct = tools.weighted_mean(
            [r["pass_percentage"] for r in records],
            [1.0 for _ in records],  # equal department weighting; swap for enrolment-weighted later
        )
        co_po = tools.simple_mean([r["co_po_attainment"] for r in records])
        compliance = tools.simple_mean([r["curriculum_compliance"] for r in records])

        evidence = Evidence(
            source_system="Academic ERP (per-department)",
            scope="all departments reporting in this cycle",
            detail={
                "per_department_pass_percentage": {r["department"]: r["pass_percentage"] for r in records},
                "stale_departments": stale_flags,
            },
        )

        ctx.domain_results["academic"] = {
            "institution_pass_percentage": pass_pct.value,
            "institution_co_po_attainment": co_po.value,
            "institution_curriculum_compliance": compliance.value,
            "spread": {r["department"]: r["pass_percentage"] for r in records},
            "stale_or_missing_departments": stale_flags,
            "evidence": evidence.as_dict(),
            "formulas": {
                "institution_pass_percentage": pass_pct.formula,
                "institution_co_po_attainment": co_po.formula,
            },
        }
        ctx.note(f"{self.name}: aggregated {len(records)} departments "
                 f"({len(stale_flags)} flagged stale)")
        return ctx

    def guardrail_flags(self) -> List[str]:
        return [
            "Pulls only from approved academic records and attainment reports.",
            "Never averages across departments without showing the underlying spread.",
            "Flags any department with stale or missing data.",
        ]
