# Assignment 10: Ops Resilience: validate, diagnose, fix

Lab 10 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 10 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

Validate, diagnose, fix

## What was built, and where

Nine checks in [`app/agents/validation/checks.py`](../../Course-Project/backend/app/agents/validation/checks.py), eight faults in `faults.py`, repair in [`app/agents/repair.py`](../../Course-Project/backend/app/agents/repair.py), budget of 3

## How to show it

New brief, "Demo: inject a failure", "A figure written by hand": failing V1, repair, all nine pass (docs/DEMO.md step 6)

## How it is proved

[`tests/agents/test_validation.py`](../../Course-Project/backend/tests/agents/test_validation.py), `test_repair.py`, `test_graph.py` (every fault, and escalation)

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/agents/test_validation.py
```

Result when this README was written: **55 passed in 0.09s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
