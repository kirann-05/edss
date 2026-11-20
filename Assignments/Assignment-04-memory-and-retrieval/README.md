# Assignment 4: Memory and Retrieval: run state apart from stored memory

Lab 4 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 4 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

Memory split: short-term run state apart from long-term memory

## What was built, and where

Run state in the graph's checkpoints; the archive of prior briefs in [`app/services/archive.py`](../../Course-Project/backend/app/services/archive.py), and with pgvector in [`app/db/archive_store.py`](../../Course-Project/backend/app/db/archive_store.py)

## How to show it

Review queue, a draft, the "Prior briefs" tab: earlier reports with what was decided and why they match

## How it is proved

[`tests/api/test_archive_publish.py`](../../Course-Project/backend/tests/api/test_archive_publish.py), [`tests/db/test_archive_store.py`](../../Course-Project/backend/tests/db/test_archive_store.py)

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/api/test_archive_publish.py tests/db/test_archive_store.py
```

Result when this README was written: **3 passed, 4 skipped in 0.27s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
