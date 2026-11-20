# Assignment 7: Agentic Node Graph: the full pipeline

Lab 7 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 7 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

The full node graph

## What was built, and where

[`app/agents/graph.py`](../../Course-Project/backend/app/agents/graph.py)

## How to show it

[`docs/diagrams/2-agent-graph.png`](../../Course-Project/docs/diagrams/2-agent-graph.png), then a run's timeline from plan lock to the human gate (docs/DEMO.md step 3)

## How it is proved

[`tests/agents/test_graph.py`](../../Course-Project/backend/tests/agents/test_graph.py)

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/agents/test_graph.py
```

Result when this README was written: **29 passed in 1.13s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
