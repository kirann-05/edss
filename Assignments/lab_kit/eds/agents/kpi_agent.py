"""
Group E: KPI Agent.

Synthesizes the four domain views into institution-wide KPIs aligned to
NIRF/NAAC and strategic-plan targets. Receives the combined output of
Groups A-D and returns a structured KPI set with targets and variance.

Guardrails: use only the approved KPI definitions and target values;
show the formula and source behind every KPI; never mask a missed
target inside a rounded or aggregated figure.

Lab 13 hook: an optional `specialist` (see eds/specialists.py) can
override which KPI pack (formulas/targets) is applied -- e.g. a NAAC-
weighted pack vs a NIRF-weighted pack -- without this agent's code
changing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from eds.agents.base import Agent, Evidence
from eds import tools


DOMAIN_KEY_BY_KPI = {
    "institution_pass_percentage": ("academic", "institution_pass_percentage"),
    "institution_co_po_attainment": ("academic", "institution_co_po_attainment"),
    "institution_publications_per_faculty": ("research", "institution_publications_per_faculty"),
    "institution_placement_percentage": ("placement", "institution_placement_percentage"),
    "institution_average_package": ("placement", "institution_average_package_lakhs"),
    "institution_budget_utilization": ("finance", "institution_budget_utilization"),
}


class KPIAgent(Agent):
    name = "KPI Agent"

    def __init__(self, specialist=None):
        self.specialist = specialist  # Lab 13 pluggable KPI pack

    def step(self, ctx, plan, connector):
        kpi_defs: Dict[str, Any] = connector.read("institutional KPIs & dashboards")
        if self.specialist is not None:
            kpi_defs = self.specialist.apply_kpi_pack(kpi_defs)

        kpis = {}
        missing_domain = []
        for kpi_name in plan.kpis:
            if kpi_name not in kpi_defs:
                continue
            if kpi_name not in DOMAIN_KEY_BY_KPI:
                continue
            domain, field = DOMAIN_KEY_BY_KPI[kpi_name]
            domain_out = ctx.domain_results.get(domain)
            if domain_out is None:
                missing_domain.append(domain)
                continue
            actual = domain_out[field]
            target = kpi_defs[kpi_name]["target"]
            var = tools.variance_against_target(actual, target)
            kpis[kpi_name] = {
                "actual": actual,
                "target": target,
                "variance": var.value,
                "status": "meets_or_exceeds_target" if var.value >= 0 else "below_target",
                "formula": kpi_defs[kpi_name]["formula"],
                "framework": kpi_defs[kpi_name]["framework"],
                "source_domain": domain,
            }

        below_target = [k for k, v in kpis.items() if v["status"] == "below_target"]

        evidence = Evidence(
            source_system="Approved KPI Definition Registry",
            scope="institution-wide, all reporting domains",
            detail={"kpis_below_target": below_target, "missing_domains": missing_domain},
        )

        ctx.kpi_result = {
            "kpis": kpis,
            "below_target": below_target,
            "missing_domains": missing_domain,
            "evidence": evidence.as_dict(),
        }
        ctx.note(f"{self.name}: synthesized {len(kpis)} KPIs "
                 f"({len(below_target)} below target)")
        return ctx

    def guardrail_flags(self) -> List[str]:
        return [
            "Uses only the approved KPI definitions and target values.",
            "Shows the formula and source behind every KPI.",
            "Never masks a missed target inside a rounded or aggregated figure.",
        ]
