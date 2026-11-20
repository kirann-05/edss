# Assignment 2: Tool-Using Agent: call data and compute

Lab 2 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 2 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

A tool-using agent that calls data and computes

## What was built, and where

Domain agents in [`app/agents/graph.py`](../../Course-Project/backend/app/agents/graph.py), calling typed connector functions; the KPI engine in [`app/kpi/engine.py`](../../Course-Project/backend/app/kpi/engine.py) and `formulas.py`

## How to show it

Dashboard, open "Placement percentage": how it is calculated, 937 over 1,250, from totals (docs/DEMO.md step 4)

## How it is proved

[`tests/kpi/test_engine.py`](../../Course-Project/backend/tests/kpi/test_engine.py), `test_formulas.py`, [`tests/agents/test_graph.py`](../../Course-Project/backend/tests/agents/test_graph.py)

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/agents/test_graph.py tests/kpi/test_engine.py
```

Result when this README was written: **59 passed in 1.15s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
