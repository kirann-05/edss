"""
Lab 7 - the full pipeline as an explicit node graph:

    graph.chain(ingest -> plan -> workers -> validate)
    graph.edge(validate --fail--> workers)     # bounded retry
    graph.edge(validate --pass--> assemble -> gate -> publish)

Lab 8 - the domain-aggregation stage is a parallel fan-out/fan-in
(Academic, Research, Placement, Finance all run at the same time; a
merge step waits for all four before KPI synthesis proceeds) -- this
mirrors the book's Hybrid Execution Methodology table exactly:

    Gate 1: access intake          -> sequential
    Parallel domain aggregation    -> parallel
    KPI synthesis                  -> sequential (after all 4 return)
    Report generation              -> sequential (after KPI set finalized)
    Stakeholder approval           -> sequential
    Dashboard update                -> parallel, after approval
"""

from __future__ import annotations

import concurrent.futures as _cf
from typing import Dict, List, Optional

from eds.agents.academic_agent import AcademicAgent
from eds.agents.research_agent import ResearchAgent
from eds.agents.placement_agent import PlacementAgent
from eds.agents.finance_agent import FinanceAgent
from eds.agents.kpi_agent import KPIAgent
from eds.agents.report_agent import ReportGenerationAgent
from eds.coordinator import Coordinator, RegenerateBudgetExhausted, RunContext
from eds.validation import ValidationAgent, ValidationReport


DOMAIN_AGENTS = {
    "academic": AcademicAgent,
    "research": ResearchAgent,
    "placement": PlacementAgent,
    "finance": FinanceAgent,
}


class GraphRunner:
    """
    Wires every specialist agent into one executable graph and runs it
    to a first, validated end-to-end draft (Lab 7), fanning the four
    domain agents out in parallel and merging before KPI synthesis
    (Lab 8).
    """

    def __init__(self, coordinator: Coordinator, connector, kpi_agent: Optional[KPIAgent] = None,
                 report_agent: Optional[ReportGenerationAgent] = None, max_workers: int = 4):
        self.coordinator = coordinator
        self.connector = connector
        self.kpi_agent = kpi_agent or KPIAgent()
        self.report_agent = report_agent or ReportGenerationAgent()
        self.max_workers = max_workers
        self.domain_agents = {name: cls() for name, cls in DOMAIN_AGENTS.items()}

    # -- Lab 8: parallel fan-out / fan-in over the domain agents -------------
    def run_domain_aggregation(self, ctx: RunContext) -> RunContext:
        domains_in_scope = [d for d in ctx.plan.domains if d in self.domain_agents]
        with _cf.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._run_one_domain, ctx, d): d
                for d in domains_in_scope
            }
            for future in _cf.as_completed(futures):
                domain = futures[future]
                partial_ctx = future.result()
                # merge only this domain's result back onto the shared ctx
                # (each agent only ever writes its own ctx.domain_results[domain] key)
                ctx.domain_results[domain] = partial_ctx.domain_results[domain]
                ctx.log.extend(partial_ctx.log)
        self.coordinator.audit.log(ctx.run_id, "Coordinator", "merge",
                                    "parallel domain aggregation complete",
                                    f"domains: {list(ctx.domain_results.keys())}")
        return ctx

    def _run_one_domain(self, ctx: RunContext, domain: str) -> RunContext:
        # Each parallel worker operates on its own isolated context copy
        # touching only ctx.domain_results[domain]; the caller merges.
        agent = self.domain_agents[domain]
        local_ctx = RunContext(run_id=ctx.run_id, plan=ctx.plan, state=ctx.state)
        local_ctx = agent.step(local_ctx, ctx.plan, self.connector)
        self.coordinator.audit.log(ctx.run_id, agent.name, "aggregate domain",
                                    f"read department reports for domain={domain}",
                                    local_ctx.log[-1] if local_ctx.log else "done")
        return local_ctx

    # -- sequential downstream stages -----------------------------------
    def run_kpi_synthesis(self, ctx: RunContext) -> RunContext:
        ctx = self.kpi_agent.step(ctx, ctx.plan, self.connector)
        self.coordinator.audit.log(ctx.run_id, self.kpi_agent.name, "synthesize KPIs",
                                    "combined all domain outputs", ctx.log[-1])
        return ctx

    def run_report_generation(self, ctx: RunContext) -> RunContext:
        ctx = self.report_agent.step(ctx, ctx.plan, self.connector)
        self.coordinator.audit.log(ctx.run_id, self.report_agent.name, "compile report",
                                    "assembled decision brief", ctx.log[-1])
        return ctx

    # -- Lab 7: validate -> regenerate back-edge (bounded) -------------------
    def validate_with_self_healing(self, ctx: RunContext) -> ValidationReport:
        report = ValidationAgent.validate(ctx, ctx.plan)
        while not report.passed:
            try:
                ctx = self._regenerate_for(ctx, report)
            except RegenerateBudgetExhausted:
                self.coordinator.audit.log(ctx.run_id, "Coordinator", "escalate",
                                            "regenerate budget exhausted",
                                            f"unresolved: {report.failing}")
                break
            report = ValidationAgent.validate(ctx, ctx.plan)
        ctx.validation_report = report.as_dict()
        return report

    def _regenerate_for(self, ctx: RunContext, report: ValidationReport) -> RunContext:
        def _fix(ctx_: RunContext) -> RunContext:
            # Regenerate only the offending stage(s), not the whole run.
            if any("figure cites its source" in f for f in report.failing):
                ctx_ = self.run_domain_aggregation(ctx_)
                ctx_ = self.run_kpi_synthesis(ctx_)
            ctx_ = self.run_report_generation(ctx_)
            return ctx_

        return self.coordinator.regenerate(ctx, _fix, report.failing)

    # -- Lab 7: the whole chain, first end-to-end draft -----------------
    def build_draft(self, ctx: RunContext) -> RunContext:
        ctx = self.run_domain_aggregation(ctx)     # parallel (Lab 8)
        ctx = self.run_kpi_synthesis(ctx)           # sequential, after all 4 return
        ctx = self.run_report_generation(ctx)        # sequential, after KPI set finalized
        self.coordinator.checkpoint(ctx)
        return ctx
