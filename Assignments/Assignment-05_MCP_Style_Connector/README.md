# Assignment 5: MCP-Style Connector (one server for all sources)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: A, Foundations

## Objective

Expose every data source through one typed connector. A single connector fronts institutional KPIs and dashboards, department reports and external benchmarks, so every agent reaches data the same governed way. The book's pitfall: no agent should touch a source directly; a bypass defeats governance later.

## Concept applied in EDSS

EDSS draws on several institutional systems (academic ERP, research office, placement cell, finance office) plus external benchmarks. All of them sit behind one `Connector` interface. Department data is guarded by an access step ("Gate 1: access intake"): a domain cannot be read until access has been granted, and the grant records who authorised it. Swapping the stub data for a real ERP or database means writing a new `Connector` subclass; the agents do not change.

## Technical stack

- Python 3, standard library only (`abc` for the interface, `copy` so callers get copies, not the source tables)
- [`eds/connector.py`](../lab_kit/eds/connector.py), backed by [`../lab_kit/data/stub_data.py`](../lab_kit/data/stub_data.py)

## Implementation

Script: [`lab05_connector.py`](lab05_connector.py)

1. Creates a `StubConnector` and tries `read("department reports", domain="academic")` before any access was granted. The connector raises `AccessDeniedError`, and the script confirms it.
2. Calls `request_access("academic", authorized_by="Registrar (demo)")`, which returns an `AccessGrant` (domain, granted_by, granted_at, scope).
3. Reads through the one surface: department reports for academic, the KPI definitions, and the external benchmarks.
4. Prints how to go live: implement the same `Connector` interface against a real system and hand that instance to the Coordinator.

Key pieces:

| Name | File | Role |
| --- | --- | --- |
| `Connector` (abstract) | [`connector.py`](../lab_kit/eds/connector.py) | `request_access()` and `read(source, **kwargs)` |
| `StubConnector` | [`connector.py`](../lab_kit/eds/connector.py) | Maps the three named sources to handlers over stub data |
| `AccessGrant`, `AccessDeniedError` | [`connector.py`](../lab_kit/eds/connector.py) | Gate 1 record and its refusal |

Source names exposed: `institutional KPIs & dashboards`, `department reports` (needs `domain=` and a grant), `external benchmarks`. An unknown source raises `ValueError`.

## How to run

```bash
cd Assignments/Assignment-05_MCP_Style_Connector
python lab05_connector.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first.

## Result / evidence

Acceptance (book): all data access goes through the connector; swapping a source needs no agent change.

From [`output/run_log.txt`](output/run_log.txt):

```
Correctly denied pre-grant access: No institution-level read access granted for domain='academic'. Call request_access() first (Gate 1: access intake).

Gate 1: access granted -> AccessGrant(domain='academic', granted_by='Registrar (demo)', ..., scope='institution-wide read-only')

connector.expose:
  read('institutional KPIs & dashboards') -> 6 definitions
  read('department reports', domain='academic') -> 4 records
  read('external benchmarks') -> ['nirf_band_placement_pct_median', 'nirf_band_publications_per_faculty_median', 'note']

ACCEPT: every read above went through `connector.read(...)`; no module imported data/stub_data.py directly.
```

The benchmark values are marked in the code as an illustrative placeholder, not a real NIRF publication. In the kit, `connector.py` is the only `eds` module that imports `stub_data`.

## In the full system

| | |
| --- | --- |
| Production code | [`app/mcp_connector/`](../../Course_Project/backend/app/mcp_connector/) (server, client, per-run tokens) and ingestion adapters in [`app/ingestion/`](../../Course_Project/backend/app/ingestion/) |
| What it does there | After a run, the Audit page shows every "Read through the connector" row with the tool name and a hash of the answer |
| Proved by | [`tests/mcp_connector/`](../../Course_Project/backend/tests/mcp_connector/) (including [`test_swap.py`](../../Course_Project/backend/tests/mcp_connector/test_swap.py): identical KPIs through MCP and directly), [`tests/ingestion/test_equivalence.py`](../../Course_Project/backend/tests/ingestion/test_equivalence.py) |
