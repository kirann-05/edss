# Assignment 8: Parallel Swarm: fan out, then merge

Lab 8 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 8 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

Parallel fan-out and merge

## What was built, and where

`Send` fan-out to the four domain agents and to option drafting, in `graph.py`

## How to show it

Run page: "4 domain agents worked at the same time (measured from the events)"; `make benchmark`

## How it is proved

[`tests/agents/test_graph.py`](../../Course-Project/backend/tests/agents/test_graph.py) (TestParallelism), [`docs/benchmark.md`](../../Course-Project/docs/benchmark.md)

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/agents/test_graph.py
```

Result when this README was written: **29 passed in 1.12s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
