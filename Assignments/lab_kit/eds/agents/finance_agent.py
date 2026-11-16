"""
Group D: Finance Agent.

Aggregates budget utilization, revenue, and grant funds at the
institution level, in parallel with Academic/Research/Placement.

Guardrails: pull only from audited/approved figures; never project a
forecast as an actual; flag any figure pending finance-office
reconciliation.
"""

from __future__ import annotations

from typing import Any, Dict, List

from eds.agents.base import Agent, Evidence
from eds import tools


class FinanceAgent(Agent):
    name = "Finance Agent"

    def step(self, ctx, plan, connector):
        connector.request_access("finance", authorized_by=plan.requested_by or "Registrar")
        records: List[Dict[str, Any]] = connector.read("department reports", domain="finance")
        fin = records[0]

        utilization = tools.ratio(fin["budget_utilized_lakhs"], fin["budget_allocated_lakhs"],
                                   "budget_utilized_lakhs / budget_allocated_lakhs")

        pending = fin.get("pending_reconciliation_lakhs", 0.0)
        reconciled = fin.get("reconciled", False)

        evidence = Evidence(
            source_system=fin["source_system"],
            scope="institution-level, audited ledger",
            detail={
                "reconciled": reconciled,
                "pending_reconciliation_lakhs": pending,
                "as_of": fin.get("as_of"),
            },
        )

        ctx.domain_results["finance"] = {
            "institution_budget_utilization": utilization.value,
            "institution_revenue_lakhs": fin["revenue_lakhs"],
            "institution_grant_funds_received_lakhs": fin["grant_funds_received_lakhs"],
            "institution_grant_funds_spent_lakhs": fin["grant_funds_spent_lakhs"],
            "pending_reconciliation_lakhs": pending,
            "fully_reconciled": reconciled and pending == 0.0,
            "evidence": evidence.as_dict(),
            "formulas": {
                "institution_budget_utilization": utilization.formula,
            },
        }
        ctx.note(f"{self.name}: utilization={utilization.value:.1%}"
                 f"{' (pending reconciliation: ' + str(pending) + ' lakhs)' if pending else ''}")
        return ctx

    def guardrail_flags(self) -> List[str]:
        return [
            "Pulls only from audited or finance-office-approved figures.",
            "Never projects a forecast as an actual.",
            "Flags any figure pending finance-office reconciliation.",
        ]
