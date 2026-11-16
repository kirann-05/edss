# Assignment 2: Tool-Using Agent (call data and compute)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: A, Foundations

## Objective

Give the agent tools it must call to act, rather than answering from memory. The agent reads institutional KPIs and department reports through readers, and computes and checks values through a typed calculator. The book's pitfall: never assert a fact in the prompt that a tool should verify.

## Concept applied in EDSS

Every number in an executive brief (placement percentage, pass percentage, budget utilisation) must come from department data and a known formula. In EDSS the agent reads the KPI definitions and the placement department reports through the connector, then computes the placement percentage with a typed `ratio` tool that returns the value, the formula and its inputs. A malformed computation is caught by the tool and marked invalid instead of being guessed.

## Technical stack

- Python 3, standard library only
- [`eds/tools.py`](../lab_kit/eds/tools.py) for typed compute tools, [`eds/connector.py`](../lab_kit/eds/connector.py) for reads
- Fictional data in [`../lab_kit/data/stub_data.py`](../lab_kit/data/stub_data.py)
- Notebook version: Google Colab / Jupyter, optional Gemini function calling with an `OfflineBrain` fallback

## Implementation

Script: [`lab02_tool_using_agent.py`](lab02_tool_using_agent.py)

1. Creates a `StubConnector` and grants read access to the `placement` domain (`request_access`).
2. `connector.read("institutional KPIs & dashboards")` returns the KPI definitions.
3. `connector.read("department reports", domain="placement")` returns the per-department placement records.
4. Sums `placed_students` and `eligible_students` across departments and calls `tools.ratio(...)` with the formula label `sum(placed_students) / sum(eligible_students)`. Asserts the result is `valid`.
5. Calls `tools.ratio(5, 0, "x / 0")` to show the tool rejecting a division by zero (`valid=False`, `note='division by zero'`).

Key pieces:

| Name | File | Role |
| --- | --- | --- |
| `ComputedValue` | [`tools.py`](../lab_kit/eds/tools.py) | Value plus formula, inputs, `valid` flag and note |
| `ratio`, `weighted_mean`, `simple_mean`, `variance_against_target` | [`tools.py`](../lab_kit/eds/tools.py) | Typed compute tools used by the domain agents |
| `StubConnector.read` | [`connector.py`](../lab_kit/eds/connector.py) | The only way to reach data |

## Notebook (Assignment 1 and 2 tasks)

[`notebook/LAB_2_Worklet15_Executive_Decision_Support.ipynb`](notebook/LAB_2_Worklet15_Executive_Decision_Support.ipynb) is the fuller Colab version. It defines eight schema-typed tools (`read_department_reports`, `read_kpi_definitions`, `read_external_benchmark`, `filter_rows`, `compute_kpi`, `compare_to_target`, `compute_variance`, `draft_notification`) and runs with or without a `GEMINI_API_KEY` (an `OfflineBrain` returns the same JSON when no key is set; the committed outputs are from an offline run).

- Assignment 1 (Cell 10): a fourth kind of tool that drafts a notification and structurally cannot send it, triggered by a defined threshold, with its justification in the trace.
- Assignment 2 (Cell 11): a read, filter, compute chain where the filter step refuses to return an empty subset.
- Cell 15 runs the rubric as assertions; Cell 16 writes [`notebook/lab2_artifacts/`](notebook/lab2_artifacts/) (tool definitions, execution trace, answers, KPI scorecard, notification draft, evaluation and acceptance results).

## How to run

```bash
cd Assignments/Assignment-02_Tool_Using_Agent
python lab02_tool_using_agent.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first.

## Result / evidence

Acceptance (book): key numbers and lookups always go through tools, never hand-done in the prompt.

From [`output/run_log.txt`](output/run_log.txt):

```
tool.read('institutional KPIs & dashboards') -> 6 KPI definitions
tool.read('department reports', domain='placement') -> 4 department records

tool.compute(...) -> placement % = 74.77%  (formula: sum(placed_students) / sum(eligible_students))

tool.compute on a malformed input -> valid=None, valid=False, note='division by zero'

ACCEPT: every figure above came from tool.read/tool.compute, none were hand-asserted.
```

(The `valid=None` in the malformed-input line is a print label quirk: the script prints the value as `None` when it is invalid, under the label `valid=`.)

Notebook evidence: [`lab2_acceptance_checks.json`](notebook/lab2_artifacts/lab2_acceptance_checks.json) records 21 of 21 checks passed (for example "8 tools, 8 schemas", "64 calls, all schema-backed", malformed arguments 3/3 rejected), and [`lab2_evaluation_results.json`](notebook/lab2_artifacts/lab2_evaluation_results.json) records 38 of 38 evaluation tests passed.

## In the full system

| | |
| --- | --- |
| Production code | Domain agents in [`app/agents/graph.py`](../../Course_Project/backend/app/agents/graph.py) calling typed connector functions; the KPI engine in [`app/kpi/engine.py`](../../Course_Project/backend/app/kpi/engine.py) and [`app/kpi/formulas.py`](../../Course_Project/backend/app/kpi/formulas.py) |
| What it does there | The dashboard's "Placement percentage" shows how it is calculated (937 over 1,250) from totals |
| Proved by | [`tests/kpi/test_engine.py`](../../Course_Project/backend/tests/kpi/test_engine.py), [`tests/kpi/test_formulas.py`](../../Course_Project/backend/tests/kpi/test_formulas.py), [`tests/agents/test_graph.py`](../../Course_Project/backend/tests/agents/test_graph.py) |
