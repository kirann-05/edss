# Assignment 7: Agentic Node Graph (the full pipeline)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: B, Orchestration

## Objective

Wire the specialist agents into one explicit graph with state and branching. The complete pipeline runs from the domain agents through KPI synthesis and report generation to validation, with a bounded validation-to-regenerate back-edge, and produces a first end-to-end draft. The book's pitfall: bound the retry edge, because an unbounded regenerate loop can spin forever.

## Concept applied in EDSS

The EDSS graph follows the worklet's hybrid execution table:

```
ingest/plan (Coordinator)
  -> Academic | Research | Placement | Finance agents   (domain aggregation)
  -> KPI Agent                                           (KPI synthesis, after all four return)
  -> Report Generation Agent                             (decision brief with options and risks)
  -> Validation Agent --fail--> regenerate (bounded)
                      --pass--> ready for the human gate (Lab 12)
```

Every agent shares one contract, `step(ctx, plan, connector)`, reads data only through the connector, writes its result into the shared `RunContext`, and attaches an evidence record. Agents never call each other; the graph runner calls them.

## Technical stack

- Python 3, standard library only (`concurrent.futures` for the domain fan-out)
- [`eds/graph.py`](../lab_kit/eds/graph.py), [`eds/validation.py`](../lab_kit/eds/validation.py), [`eds/agents/`](../lab_kit/eds/agents/)

## Implementation

Script: [`lab07_node_graph.py`](lab07_node_graph.py)

1. Builds a `StubConnector`, a `Coordinator` and a `GraphRunner`.
2. `coordinator.new_run(request)` locks a plan for all four domains.
3. `graph.build_draft(ctx)` runs the chain: `run_domain_aggregation` (the four domain agents), `run_kpi_synthesis` (KPI Agent compares each actual to its target and records variance and status), `run_report_generation` (Report Generation Agent builds KPI tables, domain breakdowns, assumptions, drill-down evidence and decision options with risks), then checkpoints.
4. `graph.validate_with_self_healing(ctx)` runs the `ValidationAgent`. On failure it calls `Coordinator.regenerate`, which counts attempts and raises `RegenerateBudgetExhausted` past `max_regenerate_attempts` (default 3). This is the bounded back-edge.
5. Prints domains, KPIs, report sections and each validation check's diagnosis, and asserts the draft passed.

Agents in the graph:

| Agent | File | Output |
| --- | --- | --- |
| Academic, Research, Placement, Finance | [`agents/academic_agent.py`](../lab_kit/eds/agents/academic_agent.py), [`research_agent.py`](../lab_kit/eds/agents/research_agent.py), [`placement_agent.py`](../lab_kit/eds/agents/placement_agent.py), [`finance_agent.py`](../lab_kit/eds/agents/finance_agent.py) | Per-domain figures plus an `Evidence` record |
| KPI Agent | [`agents/kpi_agent.py`](../lab_kit/eds/agents/kpi_agent.py) | Six KPIs with target, variance, formula, framework |
| Report Generation Agent | [`agents/report_agent.py`](../lab_kit/eds/agents/report_agent.py) | Sections, assumptions, drill-down links, options with risks |
| Validation Agent | [`validation.py`](../lab_kit/eds/validation.py) | Four named checks with a diagnosis each |

The four validation checks: every figure cites its source; assumptions are stated explicitly; each option lists its risks and trade-offs; no action is taken without leadership approval.

## How to run

```bash
cd Assignments/Assignment-07_Agentic_Node_Graph
python lab07_node_graph.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first.

## Result / evidence

Acceptance (book): one command yields a validated decision-brief draft end to end.

From [`output/run_log.txt`](output/run_log.txt):

```
Domains aggregated: ['research', 'academic', 'placement', 'finance']
KPIs synthesized: ['institution_pass_percentage', 'institution_co_po_attainment', 'institution_publications_per_faculty', 'institution_placement_percentage', 'institution_average_package', 'institution_budget_utilization']
Report sections: ['Institution-Wide KPIs vs Targets', 'Domain Breakdowns', 'Assumptions', 'Drill-Down Evidence (source of every figure)', 'Decision Options & Risks']

Validation: passed=True, failing=[]
  - assumptions are stated explicitly: 4 assumption(s) stated explicitly
...
ACCEPT: one call to build_draft() + validate_with_self_healing() produced a validated decision-brief draft end to end.
```

The domain order in the log is the order the parallel workers finished, not the plan order. The draft passed on the first validation, so no regenerate attempt was needed in this run (Lab 10 exercises the back-edge).

## In the full system

| | |
| --- | --- |
| Production code | [`app/agents/graph.py`](../../Course_Project/backend/app/agents/graph.py) |
| What it does there | The agent graph is drawn in [`docs/diagrams/2-agent-graph.png`](../../Course_Project/docs/diagrams/2-agent-graph.png); a run's timeline goes from plan lock to the human gate |
| Proved by | [`tests/agents/test_graph.py`](../../Course_Project/backend/tests/agents/test_graph.py) |
