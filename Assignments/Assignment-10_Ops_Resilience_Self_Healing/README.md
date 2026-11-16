# Assignment 10: Ops Resilience (validate, diagnose, fix)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: C, Applied reliability

## Objective

Make the pipeline self-healing when validation fails. When a check fails (every figure cites its source; assumptions are stated explicitly), the agent diagnoses the exact failing constraint and regenerates only the offending part, within a retry budget, and escalates to a human if the budget runs out. The book's pitfall: regenerate only the failing part; rebuilding everything wastes budget and churns good work.

## Concept applied in EDSS

A report-generation pass can come back broken, for example with no assumptions section or with decision options that do not list their risks. EDSS validates every draft against four named checks. Each failing check has a plain-language diagnosis, and the graph maps it to the stage that must be re-run: a missing source citation re-runs domain aggregation and KPI synthesis, while missing assumptions or option risks re-run only report generation. Attempts are counted against a budget of 3; past that the Coordinator raises `RegenerateBudgetExhausted` and the graph logs an "escalate" audit entry.

## Technical stack

- Python 3, standard library only
- [`eds/validation.py`](../lab_kit/eds/validation.py): `ValidationAgent`, `ValidationReport`, `CHECKS`
- [`eds/graph.py`](../lab_kit/eds/graph.py): `validate_with_self_healing`, `_regenerate_for`
- [`eds/coordinator.py`](../lab_kit/eds/coordinator.py): `Coordinator.regenerate`, `RegenerateBudgetExhausted`

## Implementation

Script: [`lab10_self_healing.py`](lab10_self_healing.py)

1. Builds a full draft with `GraphRunner.build_draft()` using a `Coordinator(max_regenerate_attempts=3)`.
2. Validates the clean draft as a baseline and asserts it passes.
3. Injects a fault that a broken generation step could produce: sets `ctx.report["assumptions"] = []` and replaces `ctx.report["options"]` with one option whose alternatives have no `risks` keys.
4. Validates again and asserts it now fails, printing the failing checks.
5. Calls `graph.validate_with_self_healing(ctx)`. Because the failing checks are about assumptions and option risks (not source citations), `_regenerate_for` re-runs only `run_report_generation`. `Coordinator.regenerate` increments `ctx.attempts`, logs a "self-heal" audit entry and checkpoints.
6. Asserts the report passes and that attempts used are within the budget.

Key pieces:

| Name | File | Role |
| --- | --- | --- |
| `ValidationAgent.validate` | [`validation.py`](../lab_kit/eds/validation.py) | Runs all checks, returns `passed`, `failing`, `diagnosis` |
| `GraphRunner._regenerate_for` | [`graph.py`](../lab_kit/eds/graph.py) | Chooses which stage(s) to re-run from the failing check names |
| `Coordinator.regenerate` | [`coordinator.py`](../lab_kit/eds/coordinator.py) | Bounded retry, audit, checkpoint |
| `FAILING_CHECK_TO_AGENT` | [`validation.py`](../lab_kit/eds/validation.py) | Documents which agent owns each check |

## How to run

```bash
cd Assignments/Assignment-10_Ops_Resilience_Self_Healing
python lab10_self_healing.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first.

## Result / evidence

Acceptance (book): injected faults are detected and fixed within the retry budget.

From [`output/run_log.txt`](output/run_log.txt):

```
Baseline validation (before fault injection): passed=True
...
Post-injection validation: passed=False, failing=['assumptions are stated explicitly', 'each option lists its risks and trade-offs']

After self-healing: passed=True, attempts_used=1
  - assumptions are stated explicitly: 4 assumption(s) stated explicitly
  - each option lists its risks and trade-offs: every decision option lists risks for each alternative
...
ACCEPT: injected fault was detected and fixed within the retry budget (1/3 attempts used).
```

Both injected faults were detected by name and repaired in one targeted regeneration of the report stage. The escalation path (budget exhausted) exists in the code but is not triggered by this script.

## In the full system

| | |
| --- | --- |
| Production code | Nine checks in [`app/agents/validation/checks.py`](../../Course_Project/backend/app/agents/validation/checks.py), eight injectable faults in [`app/agents/validation/faults.py`](../../Course_Project/backend/app/agents/validation/faults.py), repair in [`app/agents/repair.py`](../../Course_Project/backend/app/agents/repair.py), budget of 3 |
| What it does there | New brief with "Demo: inject a failure", "A figure written by hand": V1 fails, repair runs, all nine checks pass |
| Proved by | [`tests/agents/test_validation.py`](../../Course_Project/backend/tests/agents/test_validation.py), [`test_repair.py`](../../Course_Project/backend/tests/agents/test_repair.py), [`test_graph.py`](../../Course_Project/backend/tests/agents/test_graph.py) (every fault, and escalation) |
