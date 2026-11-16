"""
Group F: Report Generation Agent.

Compiles the leadership-ready executive report and dashboard, with
drill-down evidence back to the source department and metric, plus a
decision brief: named options with explicit risks/trade-offs for every
KPI that is off target or every flagged data-quality issue.

Guardrails: publish only Principal/Registrar-approved figures (enforced
downstream by governance, not here); keep drill-down evidence traceable
to its source system; version every executive report (handled by
governance.py).
"""

from __future__ import annotations

from typing import Any, Dict, List

from eds.agents.base import Agent


def _drill_down_links(ctx) -> List[Dict[str, Any]]:
    links = []
    for domain, result in ctx.domain_results.items():
        ev = result.get("evidence", {})
        links.append({
            "domain": domain,
            "source_system": ev.get("source_system"),
            "scope": ev.get("scope"),
            "detail": ev.get("detail"),
        })
    return links


def _decision_options(ctx) -> List[Dict[str, Any]]:
    options = []
    kpis = (ctx.kpi_result or {}).get("kpis", {})
    for name, kpi in kpis.items():
        if kpi["status"] != "below_target":
            continue
        options.append({
            "issue": f"{name} is below target ({kpi['actual']} vs target {kpi['target']}, "
                     f"variance {kpi['variance']})",
            "option_a": {
                "action": f"Escalate {kpi['source_domain']} domain to the relevant Dean for a "
                          f"root-cause review before next cycle.",
                "risks": ["Delays the corrective action by one review cycle",
                          "Requires Dean bandwidth during an already busy period"],
            },
            "option_b": {
                "action": f"Approve report for circulation with {name} flagged as an open "
                          f"watch-item and a committed remediation date.",
                "risks": ["Governing Council sees a known miss rather than a fix",
                          "Remediation date must be tracked and could slip"],
            },
        })

    # Data-quality issues also become decision items -- leadership should
    # decide how to treat metrics resting on stale/unverified/unreconciled data.
    academic = ctx.domain_results.get("academic", {})
    if academic.get("stale_or_missing_departments"):
        options.append({
            "issue": f"Stale academic data from: {academic['stale_or_missing_departments']}",
            "option_a": {
                "action": "Publish with those departments' figures marked as last-known-good, dated.",
                "risks": ["Institution-wide pass percentage may shift once refreshed"],
            },
            "option_b": {
                "action": "Hold those departments out of this cycle's institution-wide average.",
                "risks": ["Understates coverage; Council sees a partial figure"],
            },
        })

    placement = ctx.domain_results.get("placement", {})
    if placement.get("unverified_departments"):
        options.append({
            "issue": f"Unverified placement reporting from: {placement['unverified_departments']}",
            "option_a": {
                "action": "Exclude unverified departments from the institution-wide placement % "
                          "until Placement Cell verification completes.",
                "risks": ["Institution-wide figure may look lower than the true value"],
            },
            "option_b": {
                "action": "Include with a clear 'unverified' watermark on affected rows.",
                "risks": ["Risk of an unverified figure being quoted externally as final"],
            },
        })

    finance = ctx.domain_results.get("finance", {})
    if finance.get("pending_reconciliation_lakhs"):
        options.append({
            "issue": f"₹{finance['pending_reconciliation_lakhs']} lakhs pending finance-office "
                     f"reconciliation.",
            "option_a": {
                "action": "Hold budget-utilization KPI as provisional until reconciliation closes.",
                "risks": ["Council sees a 'provisional' tag on a headline finance KPI"],
            },
            "option_b": {
                "action": "Publish current utilization figure with the pending amount disclosed "
                          "as a footnote.",
                "risks": ["A materially different reconciled figure could require a correction later"],
            },
        })

    return options


class ReportGenerationAgent(Agent):
    name = "Report Generation Agent"

    def step(self, ctx, plan, connector):
        kpis = (ctx.kpi_result or {}).get("kpis", {})
        drill_down = _drill_down_links(ctx)
        options = _decision_options(ctx)

        assumptions = [
            f"Review cycle: {plan.review_cycle}",
            f"Domains in scope: {', '.join(plan.domains)}",
            "Departmental weighting for pass percentage: equal-weighted across departments "
            "(not enrolment-weighted) -- state explicitly per the acceptance checklist.",
            "Provisional placement offers are excluded from the confirmed placement percentage.",
        ]

        report = {
            "title": f"Executive Decision Brief — {plan.review_cycle}",
            "sections": [
                {"heading": "Institution-Wide KPIs vs Targets", "body": {
                    k: f"actual={v['actual']} | target={v['target']} | variance={v['variance']} "
                       f"| {v['status']} | formula: {v['formula']} | framework: {v['framework']}"
                    for k, v in kpis.items()
                }},
                {"heading": "Domain Breakdowns", "body": {
                    domain: {k: v for k, v in result.items() if k not in ("evidence",)}
                    for domain, result in ctx.domain_results.items()
                }},
                {"heading": "Assumptions", "body": assumptions},
                {"heading": "Drill-Down Evidence (source of every figure)", "body": drill_down},
                {"heading": "Decision Options & Risks", "body": options},
            ],
            "kpis": kpis,
            "drill_down": drill_down,
            "assumptions": assumptions,
            "options": options,
        }

        ctx.report = report
        ctx.note(f"{self.name}: compiled report with {len(kpis)} KPIs, "
                 f"{len(drill_down)} drill-down links, {len(options)} decision option(s)")
        return ctx

    def guardrail_flags(self) -> List[str]:
        return [
            "Publishes only Principal/Registrar-approved figures.",
            "Keeps drill-down evidence traceable to its source system.",
            "Every executive report is versioned (see governance.py).",
        ]
