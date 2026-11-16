# Assignment 11: SDLC Factory (spec to tested output)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: C, Applied reliability

## Objective

Treat the plan as a spec and the output as a tested implementation. The worklet becomes a factory: plan in, decision brief out, and the brief must pass an automated acceptance suite before the executive or leadership sees it. The book's pitfall: the acceptance suite is the gate; never let a result skip to the human without a green report.

## Concept applied in EDSS

In EDSS the locked `Plan` is the specification (review cycle, domains, KPIs, constraints) and the decision brief is the artifact built from it. The Validation Agent's checks are the acceptance suite. A "build" is one graph run; its output is eligible for the Executive/Leadership approval gate (Lab 12) only when every check is green. If the first build is not green, the self-healing loop from Lab 10 must fix it first; if it still fails, the script stops with an assertion instead of passing the brief on.

## Technical stack

- Python 3, standard library only
- [`eds/graph.py`](../lab_kit/eds/graph.py) as the build, [`eds/validation.py`](../lab_kit/eds/validation.py) as the acceptance suite

## Implementation

Script: [`lab11_sdlc_factory.py`](lab11_sdlc_factory.py)

1. `build(plan, coordinator, connector)`: creates a `GraphRunner`, starts a new run from the request (which `plan_skill` locks into a `Plan`) and calls `graph.build_draft(ctx)`. This is the book's `artifact = build(plan)`.
2. `acceptance_suite(ctx, plan)`: runs `ValidationAgent.validate(ctx, ctx.plan)`. This is `report = acceptance_suite(artifact, plan)`.
3. Prints each check as PASS or FAIL with its diagnosis.
4. If the report is not all-pass, calls `graph.validate_with_self_healing(ctx)` before allowing advancement.
5. `require report.all_pass`: asserts the final report passed. Only then does it print that the artifact is eligible for the Executive/Leadership gate.

The acceptance suite (from [`validation.py`](../lab_kit/eds/validation.py)):

| Check | What it tests |
| --- | --- |
| every figure cites its source | every domain result and the KPI result carry an evidence `source_system` |
| assumptions are stated explicitly | the report has at least one assumption |
| each option lists its risks and trade-offs | both alternatives of every decision option list risks |
| no action is taken without leadership approval | nothing is marked as published before approval |

## How to run

```bash
cd Assignments/Assignment-11_SDLC_Factory
python lab11_sdlc_factory.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first.

## Result / evidence

Acceptance (book): no decision brief advances to the executive/leadership without a fully passing acceptance report.

From [`output/run_log.txt`](output/run_log.txt):

```
Acceptance suite result: all_pass=True
  [PASS] every figure cites its source: all domain and KPI figures cite a source_system
  [PASS] assumptions are stated explicitly: 4 assumption(s) stated explicitly
  [PASS] each option lists its risks and trade-offs: every decision option lists risks for each alternative
  [PASS] no action is taken without leadership approval: no publish action has occurred prior to human approval

ACCEPT: build() produced a decision-brief artifact with a fully passing acceptance report (4/4 checks green) -- only now is it eligible for the Executive/Leadership gate.
```

In this run the first build was already green, so the self-healing branch was not needed. The failing path is demonstrated in Assignment 10.

## In the full system

| | |
| --- | --- |
| Production code | Checks V1 to V9 as a hard gate ([`app/agents/validation/checks.py`](../../Course_Project/backend/app/agents/validation/checks.py)); `make acceptance` |
| What it does there | `make acceptance` runs 94 fault trials over 18 plans, all caught and repaired, in about 2 seconds |
| Proved by | [`docs/acceptance-report.md`](../../Course_Project/docs/acceptance-report.md); the command fails if one fault slips through |
