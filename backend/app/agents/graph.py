"""The agent graph (docs/ARCHITECTURE.md section 3, Labs 7, 8, 10, 11).

    plan_lock -> access_check -> [domain agents in parallel] -> kpi_synthesis
              -> [options per off-target KPI in parallel] -> report_compose -> validate
              -> repair and validate again, at most MAX_ATTEMPTS times
              -> prepare_gate -> human_gate (stops here) -> finish

Built with LangGraph. The patterns used were checked against the current docs and a spike, not
written from memory: Send for fan-out with a merging reducer, a conditional edge for the bounded
retry, and interrupt for the human gate. A node that calls interrupt runs again from its start
when resumed, so human_gate holds no side effects, the draft is created in the node before it.

The graph stops at the gate and cannot publish: approval and release live in the governance
service, so there is no path through the graph around a person (rule 2, rule 10).
"""

import time
from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from app.agents.compose import compose_brief, figure_from, off_target, trend_word
from app.agents.connector import Connector
from app.agents.llm import ChatModel
from app.agents.models import BriefDocument, KpiFigure, OptionSet, Plan, ValidationReport
from app.agents.repair import RepairContext, repair
from app.agents.runtime import DraftSink, Runtime
from app.agents.skills.options_skill import INJECTABLE_BY_MODEL, draft_option_set
from app.agents.skills.plan_skill import DOMAIN_LABEL
from app.agents.validation.checks import ValidationContext
from app.agents.validation.faults import FAULTS, apply_fault
from app.agents.validation.suite import validate
from app.domain.enums import Domain, FactStatus
from app.domain.models import MetricFact
from app.kpi.engine import PeriodData, compute_all

# Faults that a model cannot cause, applied to the first composed draft only
POST_COMPOSE_FAULTS = tuple(f for f in FAULTS if f not in INJECTABLE_BY_MODEL)
ALL_DOMAINS = tuple(Domain)


class AccessDenied(RuntimeError):
    """A domain has no active, Registrar-authorised read scope (FR-2)."""


class PlanNotLocked(RuntimeError):
    pass


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    """The reducer that joins parallel branches: each writes its own key, so nothing collides."""
    return {**(left or {}), **(right or {})}


def concat(left: list | None, right: list | None) -> list:
    return [*(left or []), *(right or [])]


class RunState(TypedDict, total=False):
    run_id: str
    created_by: str
    plan: dict[str, Any]  # the locked plan, as data
    faults: list[str]  # demo and test failure injection, synthetic mode only
    scope: dict[str, Any]
    domain_views: Annotated[dict[str, Any], merge_dicts]
    facts: list[dict[str, Any]]
    figures: list[dict[str, Any]]  # straight from the KPI engine
    option_sets: Annotated[dict[str, Any], merge_dicts]
    brief: dict[str, Any]
    validation: dict[str, Any]
    reports: Annotated[list[dict[str, Any]], concat]
    repair_log: Annotated[list[str], concat]
    attempts: int
    escalated: bool
    brief_id: str
    gate: dict[str, Any]
    status: str
    published_version: int | None


def initial_state(
    run_id: str, plan: Plan, created_by: str, faults: list[str] | None = None
) -> RunState:
    return RunState(
        run_id=run_id,
        created_by=created_by,
        plan=plan.model_dump(mode="json"),
        faults=list(faults or []),
        attempts=0,
        reports=[],
        repair_log=[],
        status="running",
    )


@dataclass
class GraphDeps:
    connector: Connector
    model: ChatModel
    runtime: Runtime
    create_draft: DraftSink
    max_attempts: int = 3
    source_latency: float = (
        0.0  # seconds a domain agent waits on its source, to model a slow system
    )


def run_config(run_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": run_id}, "recursion_limit": 60}


def build_graph(deps: GraphDeps, checkpointer: Any):
    rt, conn = deps.runtime, deps.connector

    def plan_of(state: dict[str, Any]) -> Plan:
        return Plan.model_validate(state["plan"])

    def figures_of(state: dict[str, Any]) -> list[KpiFigure]:
        return [KpiFigure.model_validate(f) for f in state.get("figures", [])]

    def facts_of(state: dict[str, Any]) -> dict[int, MetricFact]:
        return {f["id"]: MetricFact.model_validate(f) for f in state.get("facts", [])}

    def validation_context(state: dict[str, Any]) -> ValidationContext:
        plan = plan_of(state)
        facts = facts_of(state)
        sources = {
            s.id: s
            for s in (conn.get_source(sid) for sid in {f.source_system_id for f in facts.values()})
            if s is not None
        }
        return ValidationContext(
            plan=plan,
            facts=facts,
            sources=sources,
            publications=tuple(conn.get_publications(plan.period_year)),
            definitions={d.key: d for d in conn.get_kpi_definitions()},
        )

    def repair_context(state: dict[str, Any]) -> RepairContext:
        plan = plan_of(state)
        return RepairContext(
            plan=plan,
            figures={f.key: f for f in figures_of(state)},
            health=tuple(conn.get_data_health(plan.period_year)),
            model=deps.model,
        )

    # --- nodes -----------------------------------------------------------------------------
    @rt.traced("plan_lock", "Plan locked")
    def plan_lock(state: dict[str, Any]) -> dict[str, Any]:
        if not plan_of(state).locked:
            raise PlanNotLocked("the plan must be locked before any work begins")
        return {}

    @rt.traced("access_check", "Access check")
    def access_check(state: dict[str, Any]) -> dict[str, Any]:
        plan, today = plan_of(state), conn.today()
        grants = {
            g.domain: g
            for g in conn.get_scope_grants()
            if g.active and g.dept_code is None and (g.expires_on is None or g.expires_on >= today)
        }
        missing = [d for d in plan.domains if d not in grants]
        if missing:
            names = ", ".join(DOMAIN_LABEL.get(d, d.value) for d in missing)
            raise AccessDenied(f"No Registrar-authorised access to {names}")
        return {
            "scope": {
                d.value: {
                    "granted_by": grants[d].granted_by,
                    "expires_on": str(grants[d].expires_on),
                }
                for d in plan.domains
            }
        }

    def fan_out_domains(state: dict[str, Any]) -> list[Send]:
        plan = plan_of(state)
        return [
            Send(
                "domain_agent",
                {"run_id": state["run_id"], "domain": d.value, "period": plan.period_year},
            )
            for d in plan.domains
        ]

    @rt.traced(
        "domain_agent",
        lambda s: f"{DOMAIN_LABEL[Domain(s['domain'])]} agent",
        node_id=lambda s: f"domain:{s['domain']}",
    )
    def domain_agent(state: dict[str, Any]) -> dict[str, Any]:
        if deps.source_latency:
            time.sleep(deps.source_latency)  # a real source system would take about this long
        facts = conn.get_domain_metrics(Domain(state["domain"]), state["period"])
        by_dept: dict[str, dict[str, Any]] = {}
        for fact in facts:
            entry = by_dept.setdefault(
                fact.dept_code, {"facts": 0, "oldest_as_of": str(fact.as_of), "non_final": 0}
            )
            entry["facts"] += 1
            entry["oldest_as_of"] = min(entry["oldest_as_of"], str(fact.as_of))
            entry["non_final"] += fact.status not in (FactStatus.FINAL, FactStatus.AUDITED)
        view = {
            "domain": state["domain"],
            "fact_count": len(facts),
            "departments": by_dept,
            "facts": [f.model_dump(mode="json") for f in facts],
        }
        return {"domain_views": {state["domain"]: view}}

    @rt.traced("kpi_synthesis", "KPI synthesis")
    def kpi_synthesis(state: dict[str, Any]) -> dict[str, Any]:
        plan = plan_of(state)
        period = plan.period_year
        departments = tuple(conn.list_departments())
        definitions = [d for d in conn.get_kpi_definitions() if d.active]

        def results_for(for_period: str, facts: list[MetricFact]):
            data = PeriodData(
                period_year=for_period,
                departments=departments,
                facts=tuple(facts),
                publications=tuple(conn.get_publications(for_period)),
                is_current=for_period == conn.current_period(),
            )
            targets = {t.kpi_key: t for t in conn.get_targets(for_period)}
            computed = compute_all(
                definitions, targets, data, conn.today(), conn.stale_after_days()
            )
            return {r.kpi_key: r for r in computed}

        # the four domain agents' views, joined, plus the reference counts every ratio divides by
        facts = [
            MetricFact.model_validate(f)
            for view in state["domain_views"].values()
            for f in view["facts"]
        ]
        facts += list(conn.get_domain_metrics(Domain.REFERENCE, period))
        current = results_for(period, facts)

        periods = conn.periods()
        earlier = (
            periods[periods.index(period) - 1]
            if period in periods and periods.index(period) > 0
            else None
        )
        previous: dict[str, Any] = {}
        if earlier is not None:
            earlier_facts = [f for d in ALL_DOMAINS for f in conn.get_domain_metrics(d, earlier)]
            previous = results_for(earlier, earlier_facts)

        figures = []
        for definition in definitions:
            if definition.key not in plan.kpi_keys:
                continue
            result = current[definition.key]
            before = previous.get(definition.key)
            trend = trend_word(
                result.value,
                before.value if before else None,
                result.target,
                definition.higher_is_better,
            )
            figures.append(figure_from(definition, result, trend))
        return {
            "figures": [f.model_dump(mode="json") for f in figures],
            "facts": [f.model_dump(mode="json") for f in facts],
        }

    def fan_out_options(state: dict[str, Any]) -> list[Send] | str:
        plan = plan_of(state)
        needing = off_target(figures_of(state), plan.options_for)
        if not needing:
            return "report_compose"
        faults = [f for f in state.get("faults", []) if f in INJECTABLE_BY_MODEL]
        fault_fact = next(
            (
                f["id"]
                for f in state.get("facts", [])
                if f["status"] == FactStatus.PROVISIONAL.value
            ),
            None,
        )
        return [
            Send(
                "draft_options",
                {
                    "run_id": state["run_id"],
                    "figure": figure.model_dump(mode="json"),
                    # a misbehaving model is simulated on the first KPI only, so repair has one thing to fix
                    "inject": faults if index == 0 else [],
                    "fault_fact_id": fault_fact if index == 0 else None,
                },
            )
            for index, figure in enumerate(needing)
        ]

    @rt.traced(
        "draft_options",
        lambda s: f"Options for {s['figure']['key']}",
        node_id=lambda s: f"options:{s['figure']['key']}",
    )
    def draft_options(state: dict[str, Any]) -> dict[str, Any]:
        figure = KpiFigure.model_validate(state["figure"])
        option_set = draft_option_set(
            deps.model,
            figure,
            attempt=1,
            inject=state.get("inject", ()),
            fault_fact_id=state.get("fault_fact_id"),
        )
        return {"option_sets": {figure.key: option_set.model_dump(mode="json")}}

    @rt.traced("report_compose", "Brief composed")
    def report_compose(state: dict[str, Any]) -> dict[str, Any]:
        plan = plan_of(state)
        sets = [OptionSet.model_validate(s) for s in state.get("option_sets", {}).values()]
        document = compose_brief(
            plan, figures_of(state), sets, list(conn.get_data_health(plan.period_year))
        )
        if state.get("attempts", 0) == 0:
            context = validation_context(state)
            for fault in state.get("faults", []):
                if fault in POST_COMPOSE_FAULTS:
                    document = apply_fault(document, fault, context)
        return {"brief": document.model_dump(mode="json")}

    @rt.traced(
        "validate",
        lambda s: f"Validation, attempt {s.get('attempts', 0) + 1}",
        outcome=lambda update: ValidationReport.model_validate(update["validation"]).passed,
        detail=lambda update: _validation_detail(update["validation"]),
    )
    def validate_node(state: dict[str, Any]) -> dict[str, Any]:
        document = BriefDocument.model_validate(state["brief"])
        attempt = state.get("attempts", 0) + 1
        report = validate(document, validation_context(state), attempt)
        dumped = report.model_dump(mode="json")
        return {"validation": dumped, "reports": [dumped], "attempts": attempt}

    def after_validate(state: dict[str, Any]) -> Literal["regenerate", "prepare_gate"]:
        report = ValidationReport.model_validate(state["validation"])
        # bounded (rule 8): when the budget is spent the draft goes to a person, flagged
        if report.passed or state["attempts"] >= deps.max_attempts:
            return "prepare_gate"
        return "regenerate"

    @rt.traced("regenerate", lambda s: f"Repair, attempt {s.get('attempts', 0) + 1}")
    def regenerate(state: dict[str, Any]) -> dict[str, Any]:
        document = BriefDocument.model_validate(state["brief"])
        report = ValidationReport.model_validate(state["validation"])
        fixed, log = repair(document, report, repair_context(state), attempt=state["attempts"] + 1)
        return {"brief": fixed.model_dump(mode="json"), "repair_log": log}

    @rt.traced("prepare_gate", "Draft ready for review")
    def prepare_gate(state: dict[str, Any]) -> dict[str, Any]:
        report = ValidationReport.model_validate(state["validation"])
        escalated = not report.passed
        diagnosis = (
            "; ".join(v.diagnosis for c in report.failing for v in c.violations)[:2000]
            if escalated
            else None
        )
        brief_id = deps.create_draft(
            run_id=state["run_id"],
            document=BriefDocument.model_validate(state["brief"]),
            validation=report,
            attempts=state["attempts"],
            escalated=escalated,
            diagnosis=diagnosis,
            repair_log=tuple(state.get("repair_log", [])),
            history=tuple(ValidationReport.model_validate(x) for x in state.get("reports", [])),
            created_by=state["created_by"],
        )
        return {"brief_id": brief_id, "escalated": escalated}

    def human_gate(state: dict[str, Any]) -> dict[str, Any]:
        # No side effects before interrupt: this node runs again from the top when resumed.
        decision = interrupt(
            {
                "run_id": state["run_id"],
                "brief_id": state["brief_id"],
                "escalated": state["escalated"],
            }
        )
        return {"gate": decision}

    @rt.traced("finish", "Decision recorded")
    def finish(state: dict[str, Any]) -> dict[str, Any]:
        gate = state.get("gate") or {}
        return {"status": "completed", "published_version": gate.get("version")}

    # --- wiring ----------------------------------------------------------------------------
    graph = StateGraph(RunState)
    for name, fn in (
        ("plan_lock", plan_lock),
        ("access_check", access_check),
        ("domain_agent", domain_agent),
        ("kpi_synthesis", kpi_synthesis),
        ("draft_options", draft_options),
        ("report_compose", report_compose),
        ("validate", validate_node),
        ("regenerate", regenerate),
        ("prepare_gate", prepare_gate),
        ("human_gate", human_gate),
        ("finish", finish),
    ):
        graph.add_node(name, fn)

    graph.add_edge(START, "plan_lock")
    graph.add_edge("plan_lock", "access_check")
    graph.add_conditional_edges("access_check", fan_out_domains, ["domain_agent"])
    graph.add_edge("domain_agent", "kpi_synthesis")  # waits for every parallel agent: the join
    graph.add_conditional_edges(
        "kpi_synthesis", fan_out_options, ["draft_options", "report_compose"]
    )
    graph.add_edge("draft_options", "report_compose")
    graph.add_edge("report_compose", "validate")
    graph.add_conditional_edges("validate", after_validate, ["regenerate", "prepare_gate"])
    graph.add_edge("regenerate", "validate")  # the bounded back-edge
    graph.add_edge("prepare_gate", "human_gate")
    graph.add_edge("human_gate", "finish")
    graph.add_edge("finish", END)
    return graph.compile(checkpointer=checkpointer)


def _validation_detail(report: dict[str, Any]) -> str:
    failing = [c["id"] for c in report["checks"] if not c["passed"]]
    return f"Failing: {', '.join(failing)}" if failing else "All nine checks passed"
