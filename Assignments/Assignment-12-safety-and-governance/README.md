# Assignment 12: Safety and Governance: approval, evaluation, rollback

Lab 12 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 12 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

Safety and governance: approval, evaluation, rollback

## What was built, and where

[`app/governance/service.py`](../../Course-Project/backend/app/governance/service.py), [`app/core/rbac.py`](../../Course-Project/backend/app/core/rbac.py)

## How to show it

Principal edits and approves; Reports: compare versions, roll back with a reason; HOD sees only their department (docs/DEMO.md steps 7 to 9)

## How it is proved

[`tests/governance/test_governance.py`](../../Course-Project/backend/tests/governance/test_governance.py), [`tests/api/test_scoping.py`](../../Course-Project/backend/tests/api/test_scoping.py), `test_authorization.py`, the browser tests

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/api/test_scoping.py tests/governance/test_governance.py
```

Result when this README was written: **73 passed in 0.29s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
