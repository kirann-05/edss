# Assignment 5: MCP-Style Connector: one server for all sources

Lab 5 of the Agentic AI build book, applied to the Executive Decision Support System (EDSS). The course project is divided across the labs; this assignment is the slice of it that Lab 5 asks for. The code lives in [`Course-Project/`](../../Course-Project/), not copied here, so there is one source of truth.

## What the lab asks for

An MCP-style connector: one server for all sources

## What was built, and where

[`app/mcp_connector/`](../../Course-Project/backend/app/mcp_connector/) (server, client, per-run tokens), ingestion adapters in [`app/ingestion/`](../../Course-Project/backend/app/ingestion/)

## How to show it

Run a brief, then Audit: every "Read through the connector" row, with the tool and a hash of the answer

## How it is proved

[`tests/mcp_connector/`](../../Course-Project/backend/tests/mcp_connector/) (swap test: identical KPIs through MCP and directly), [`tests/ingestion/test_equivalence.py`](../../Course-Project/backend/tests/ingestion/test_equivalence.py)

Run the tests for this lab (from the repository root):

```bash
cd Course-Project/backend
uv run pytest -q tests/ingestion/test_equivalence.py tests/mcp_connector/
```

Result when this README was written: **39 passed in 2.41s**.

## Links

- Back to the [assignments overview](../README.md) and the [main README](../../README.md)
- The lab map for all labs: [`Course-Project/docs/LABS.md`](../../Course-Project/docs/LABS.md)
- The full technical documentation: [`Course-Project/docs/technical/`](../../Course-Project/docs/technical/README.md)
