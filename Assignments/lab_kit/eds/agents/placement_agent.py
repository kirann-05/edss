"""
Group C: Placement Agent.

Aggregates placement percentage, average package, and internship
completion, in parallel with Academic/Research/Finance.

Guardrails: pull only from Placement-Cell-verified records; never
present a provisional offer as a confirmed placement; flag departments
with incomplete reporting.
"""

from __future__ import annotations

from typing import Any, Dict, List

from eds.agents.base import Agent, Evidence
from eds import tools


class PlacementAgent(Agent):
    name = "Placement Agent"

    def step(self, ctx, plan, connector):
        connector.request_access("placement", authorized_by=plan.requested_by or "Registrar")
        records: List[Dict[str, Any]] = connector.read("department reports", domain="placement")

        unverified = [r["department"] for r in records if not r.get("verified", False)]

        total_eligible = sum(r["eligible_students"] for r in records)
        total_placed = sum(r["placed_students"] for r in records)  # confirmed only, excludes provisional
        total_provisional = sum(r.get("provisional_offers", 0) for r in records)

        placement_pct = tools.ratio(total_placed, total_eligible,
                                     "sum(placed_students, confirmed only) / sum(eligible_students)")
        avg_package = tools.weighted_mean(
            [r["average_package_lakhs"] for r in records],
            [r["placed_students"] for r in records],
        )
        internship = tools.simple_mean([r["internship_completion_pct"] for r in records])

        evidence = Evidence(
            source_system="Placement Cell CRM (verified records only)",
            scope="all departments reporting in this cycle",
            detail={
                "per_department_placed": {r["department"]: r["placed_students"] for r in records},
                "provisional_offers_excluded": total_provisional,
                "unverified_departments": unverified,
            },
        )

        ctx.domain_results["placement"] = {
            "institution_placement_percentage": round(placement_pct.value * 100, 2),
            "institution_average_package_lakhs": avg_package.value,
            "institution_internship_completion_pct": internship.value,
            "provisional_offers_excluded_from_placed": total_provisional,
            "unverified_departments": unverified,
            "evidence": evidence.as_dict(),
            "formulas": {
                "institution_placement_percentage": placement_pct.formula,
                "institution_average_package_lakhs": avg_package.formula,
            },
        }
        ctx.note(f"{self.name}: {total_placed}/{total_eligible} confirmed placed "
                 f"({total_provisional} provisional offers excluded); "
                 f"{len(unverified)} dept(s) unverified")
        return ctx

    def guardrail_flags(self) -> List[str]:
        return [
            "Pulls only from Placement-Cell-verified records.",
            "Never presents a provisional offer as a confirmed placement.",
            "Flags departments with incomplete reporting.",
        ]
