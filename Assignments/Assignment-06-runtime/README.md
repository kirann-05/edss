# Assignment 6: Runtime: skills, tools, memory and audit under control

Lab 6 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 6 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

Runtime: skills, tools, memory and audit under control

## What was built, and where

[`app/agents/runtime.py`](../../Course-Project/backend/app/agents/runtime.py) (traced steps, budget), [`app/governance/audit.py`](../../Course-Project/backend/app/governance/audit.py) (hash chain), checkpoints

## How to show it

Audit page: "The audit chain verifies", a run's trace step by step

## How it is proved

[`tests/governance/test_audit.py`](../../Course-Project/backend/tests/governance/test_audit.py), [`tests/api/test_audit_api.py`](../../Course-Project/backend/tests/api/test_audit_api.py) (tampering found at the row), [`tests/db/test_audit_store.py`](../../Course-Project/backend/tests/db/test_audit_store.py)

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/api/test_audit_api.py tests/db/test_audit_store.py tests/governance/test_audit.py
```

Result when this README was written: **34 passed, 10 skipped in 0.74s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
