"""
Group B: Research Agent.

Aggregates publications, citations, and grants across departments, in
parallel with Academic/Placement/Finance.

Guardrails: pull only from validated records; never double-count a
cross-department collaboration; cite the source system behind every
figure.
"""

from __future__ import annotations

from typing import Any, Dict, List

from eds.agents.base import Agent, Evidence
from eds import tools


class ResearchAgent(Agent):
    name = "Research Agent"

    def step(self, ctx, plan, connector):
        connector.request_access("research", authorized_by=plan.requested_by or "Registrar")
        records: List[Dict[str, Any]] = connector.read("department reports", domain="research")

        pubs = tools.dedup_sum_by_collaboration(records, count_field="publications")
        citations = tools.simple_mean([r["citations"] for r in records])
        grants = sum(r["grants_secured_lakhs"] for r in records)

        faculty_count = connector.total_faculty_count()
        per_faculty = tools.ratio(pubs.value, faculty_count,
                                   "sum(publications, de-duplicated) / total_faculty_count")

        evidence = Evidence(
            source_system="Research Office Registry",
            scope="all departments reporting in this cycle",
            detail={
                "per_department_publications": {r["department"]: r["publications"] for r in records},
                "shared_collaborations": pubs.inputs.get("shared_collaboration_ids", []),
                "dedup_note": pubs.note,
            },
        )

        ctx.domain_results["research"] = {
            "institution_publications_total": pubs.value,
            "institution_publications_per_faculty": per_faculty.value,
            "institution_citations_avg": citations.value,
            "institution_grants_secured_lakhs": grants,
            "evidence": evidence.as_dict(),
            "formulas": {
                "institution_publications_per_faculty": per_faculty.formula,
                "institution_publications_total": pubs.formula,
            },
        }
        ctx.note(f"{self.name}: aggregated {len(records)} departments; {pubs.note}")
        return ctx

    def guardrail_flags(self) -> List[str]:
        return [
            "Pulls only from validated publication and grant records.",
            "Never double-counts a cross-department collaboration.",
            "Cites the source system behind every figure.",
        ]
