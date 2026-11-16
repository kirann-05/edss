"""
Dashboard data export.

Produces the four panels described in the build book
(Institution KPIs / Domain metrics / Drill-down evidence / Executive
report) as one JSON-serializable payload. A separate front-end
(dashboard_template/executive_decision_dashboard_template.html, or the
published Cowork artifact) renders this payload -- this module has no
HTML in it on purpose, so the data shape is stable regardless of how
it's displayed.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from eds.coordinator import RunContext
from eds.governance import PublishedVersion, Governance


def build_dashboard_payload(ctx: RunContext, governance: Governance,
                             published: Optional[PublishedVersion] = None,
                             audit_entries: Optional[list] = None) -> Dict[str, Any]:
    kpis = (ctx.kpi_result or {}).get("kpis", {})
    return {
        "run_id": ctx.run_id,
        "review_cycle": ctx.plan.review_cycle,
        "plan": ctx.plan.as_dict(),
        "panels": {
            "institution_kpis": kpis,
            "domain_metrics": {
                domain: {k: v for k, v in result.items() if k != "evidence"}
                for domain, result in ctx.domain_results.items()
            },
            "drill_down_evidence": (ctx.report or {}).get("drill_down", []),
            "executive_report": {
                "title": (ctx.report or {}).get("title"),
                "assumptions": (ctx.report or {}).get("assumptions", []),
                "decision_options": (ctx.report or {}).get("options", []),
                "status": published.content.get("status") if published else "draft",
                "approved_by": published.approved_by if published else None,
                "approver_role": published.role if published else None,
                "version": published.version if published else None,
                "published_at": published.published_at if published else None,
            },
        },
        "validation": ctx.validation_report,
        "attempts": ctx.attempts,
        "audit_trail": audit_entries or [],
        "version_history": governance.history() if governance else [],
        "metrics": governance.metrics if governance else [],
    }
