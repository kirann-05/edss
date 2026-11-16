# Assignment 6: Agent Runtime (skills, tools, memory, audit)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: A, Foundations

## Objective

Run the agent inside a controlled runtime with a full audit log. The runtime binds skills, tools and memory behind the loop, enforces budgets and approval gates, logs every step and checkpoints state, so it becomes the backbone later labs plug into. The book's pitfall: log inputs and outputs, not just messages, and checkpoint before risky steps or a resume loses state.

## Concept applied in EDSS

An executive brief touches confidential institutional data and ends in a leadership decision, so every step must be traceable. In EDSS the Coordinator writes an append-only audit entry for each action (who, intent, action, result summary) and checkpoints the run context to disk after each step. If the process dies mid-run, a fresh Coordinator can reload the last checkpoint and continue from the same state.

## Technical stack

- Python 3, standard library only (`json`, `uuid`, `pathlib`)
- [`eds/coordinator.py`](../lab_kit/eds/coordinator.py): `Coordinator`, `AuditLog`, `RunContext`
- [`eds/runtime.py`](../lab_kit/eds/runtime.py): the full `Runtime` class with a step budget and gated actions (used by the Lab 14 capstone)
- Output as JSON Lines (audit) and JSON (checkpoints)

## Implementation

Script: [`lab06_runtime.py`](lab06_runtime.py)

1. Deletes any old `output/audit_log.jsonl`, then creates an `AuditLog` that writes to it and a `Coordinator` with `checkpoint_dir=output/checkpoints`.
2. `coordinator.new_run(...)` locks a plan for academic and finance, writes the first audit entry ("start run") and the first checkpoint.
3. Loops over two steps, "academic aggregation" and "finance aggregation". Each step is simulated: it adds a note to the run log, writes an audit entry, and checkpoints. (The `if "risky" in step_name` branch is a placeholder for `wait_for_approval`; neither step is risky.)
4. Prints the audit log.
5. Simulates a crash by creating a brand new `Coordinator` that shares only the checkpoint folder, and calls `resume(run_id)`. Asserts that at least 3 actions were audited and that the resumed log equals the pre-crash log.

Key pieces:

| Name | File | Role |
| --- | --- | --- |
| `AuditLog.log` | [`coordinator.py`](../lab_kit/eds/coordinator.py) | Appends `{ts, run_id, actor, intent, action, result_summary}` to memory and to the JSONL file |
| `Coordinator.checkpoint` | [`coordinator.py`](../lab_kit/eds/coordinator.py) | Writes plan, domain results, KPIs, report, validation, approval, attempts and log to `<run_id>.json` |
| `Coordinator.resume` | [`coordinator.py`](../lab_kit/eds/coordinator.py) | Reloads that snapshot |
| `Runtime` (budget, `GATED_ACTIONS = {"publish"}`) | [`runtime.py`](../lab_kit/eds/runtime.py) | The full runtime wrapper; not called by this script |

Note: this script demonstrates audit and checkpoint/resume. The step budget and the publish gate are implemented in `Runtime` and exercised in the capstone ([`../lab_kit/labs/lab14_capstone.py`](../lab_kit/labs/lab14_capstone.py)), not here.

## How to run

```bash
cd Assignments/Assignment-06_Agent_Runtime
python lab06_runtime.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first.

## Result / evidence

Acceptance (book): every action is logged with inputs/outputs; a crashed run resumes from its last checkpoint.

From [`output/run_log.txt`](output/run_log.txt):

```
  [2026-11-16T20:22:00.535824] Coordinator :: start run -> locked plan for 'Q1 FY26 (Lab 6 demo)' covering ['academic', 'finance']
  [2026-11-16T20:22:00.535824] Coordinator :: run academic aggregation -> simulated step: academic aggregation would run here
  [2026-11-16T20:22:00.536824] Coordinator :: run finance aggregation -> simulated step: finance aggregation would run here

Simulating a crash and resuming from the last checkpoint in a fresh process...
Resumed run 4ab6e706 at attempt=0, log has 2 entries:
...
ACCEPT: every action was logged with inputs/outputs, and the resumed run's state matches the pre-crash state exactly.
```

Output files:

- [`output/audit_log.jsonl`](output/audit_log.jsonl): the three audit entries for run `4ab6e706` (timestamps are UTC).
- [`output/checkpoints/4ab6e706.json`](output/checkpoints/4ab6e706.json): the checkpoint the resume read.

## In the full system

| | |
| --- | --- |
| Production code | [`app/agents/runtime.py`](../../Course_Project/backend/app/agents/runtime.py) (traced steps, budget), [`app/governance/audit.py`](../../Course_Project/backend/app/governance/audit.py) (hash chain), graph checkpoints |
| What it does there | The Audit page shows "The audit chain verifies" and a run's trace step by step |
| Proved by | [`tests/governance/test_audit.py`](../../Course_Project/backend/tests/governance/test_audit.py), [`tests/api/test_audit_api.py`](../../Course_Project/backend/tests/api/test_audit_api.py) (tampering found at the row), [`tests/db/test_audit_store.py`](../../Course_Project/backend/tests/db/test_audit_store.py) |
