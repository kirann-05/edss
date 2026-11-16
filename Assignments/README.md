# Lab Assignments: Executive Decision Support System (EDSS)

Course: Agentic AI (26ECAC401), KLE Technological University
Team project: Executive Decision Support System, Chapter 15 / Worklet 15 of the 14-Lab Build Book

This folder holds one assignment per lab for Labs 1 to 12. Each assignment is a small, runnable Python script that adds one agentic capability to the EDSS worklet, plus the real console output of a run as evidence. Labs 13 and 14 are bridge labs that lead into the full course project in [`../Course_Project/`](../Course_Project/).

## Overview

| # | Lab | Concept | Folder | Result (from `output/run_log.txt`) |
| --- | --- | --- | --- | --- |
| 1 | Agent vs Chatbot | Clarify, plan, revise loop instead of a one-shot answer | [Assignment-01_Agent_vs_Chatbot](Assignment-01_Agent_vs_Chatbot/) | 2 clarifying questions asked for an empty request; plan produced and revised to academic + finance. Notebook: 16/16 checks |
| 2 | Tool-Using Agent | Numbers come from typed tools, not the prompt | [Assignment-02_Tool_Using_Agent](Assignment-02_Tool_Using_Agent/) | Placement 74.77% computed by `tools.ratio`; division by zero returned `valid=False`. Notebook: 21/21 checks, 38/38 evaluation tests |
| 3 | Skill Creation | Reusable, typed plan and format skills | [Assignment-03_Skill_Creation](Assignment-03_Skill_Creation/) | Same skills ran unchanged for a Q1 review and a NAAC snapshot; mutation of the locked plan rejected |
| 4 | Memory and Retrieval | Short-term run state vs long-term store | [Assignment-04_Memory_and_Retrieval](Assignment-04_Memory_and_Retrieval/) | Tag search returned `2025-Q4`, `2025-Q3`; similarity ranked the placement report first |
| 5 | MCP-Style Connector | One governed connector for every source | [Assignment-05_MCP_Style_Connector](Assignment-05_MCP_Style_Connector/) | Read before access grant denied; 6 KPI definitions, 4 academic records, benchmarks read through `connector.read` |
| 6 | Agent Runtime | Audit log, checkpoint and resume | [Assignment-06_Agent_Runtime](Assignment-06_Agent_Runtime/) | 3 audited actions; a fresh Coordinator resumed run `4ab6e706` with identical state |
| 7 | Agentic Node Graph | The full pipeline as an explicit graph with a bounded back-edge | [Assignment-07_Agentic_Node_Graph](Assignment-07_Agentic_Node_Graph/) | 4 domains, 6 KPIs, 5 report sections; validation `passed=True` |
| 8 | Parallel Swarm | Fan-out over domain agents, merge by plan coverage | [Assignment-08_Parallel_Swarm](Assignment-08_Parallel_Swarm/) | Sequential 1.40 s vs parallel 0.36 s (3.88x); same results, full coverage |
| 9 | Deep Research | Every figure grounded in in-scope evidence | [Assignment-09_Deep_Research_Grounding](Assignment-09_Deep_Research_Grounding/) | 2 grounded candidates accepted, 1 uncited candidate rejected |
| 10 | Ops Resilience | Validate, diagnose, regenerate only the failing part | [Assignment-10_Ops_Resilience_Self_Healing](Assignment-10_Ops_Resilience_Self_Healing/) | 2 injected faults detected and repaired in 1 of 3 allowed attempts |
| 11 | SDLC Factory | Plan as spec, acceptance suite as the gate | [Assignment-11_SDLC_Factory](Assignment-11_SDLC_Factory/) | 4/4 acceptance checks green before the leadership gate |
| 12 | Safety and Governance | Approval gate, versioning, metrics, rollback | [Assignment-12_Safety_and_Governance](Assignment-12_Safety_and_Governance/) | Unauthorised role and unapproved publish rejected; v1, v2 published; rollback to v1 recorded as v3 |

Each assignment folder contains:

- `labNN_*.py`: the runnable script for that lab
- `README.md`: objective, how it maps to EDSS, implementation, how to run, evidence, and the production equivalent in the course project
- `output/run_log.txt`: the console output of a real run, plus any artifacts the lab writes (audit log and checkpoints in Lab 6, published versions in Lab 12)
- Assignments 1 and 2 also have a `notebook/` folder with the Colab notebook and its JSON artifacts

## How the lab kit works

All scripts share one small package, [`lab_kit/`](lab_kit/). It uses only the Python standard library (pytest is needed only for the tests). Each script adds `lab_kit/` to `sys.path` and imports from the `eds` package, so it can be run from its own folder.

| Path | What it holds |
| --- | --- |
| [`lab_kit/eds/connector.py`](lab_kit/eds/connector.py) | Lab 5: the `Connector` interface and `StubConnector`, the only module that reads the stub data |
| [`lab_kit/eds/tools.py`](lab_kit/eds/tools.py) | Lab 2: typed compute tools returning `ComputedValue` |
| [`lab_kit/eds/skills.py`](lab_kit/eds/skills.py) | Lab 3: `plan_skill`, the frozen `Plan`, `format_decision_skill` |
| [`lab_kit/eds/memory.py`](lab_kit/eds/memory.py) | Lab 4: `RunState` and `LongTermStore` |
| [`lab_kit/eds/coordinator.py`](lab_kit/eds/coordinator.py) | Labs 1, 6, 10: clarify/plan/revise, audit log, checkpoints, bounded regenerate |
| [`lab_kit/eds/runtime.py`](lab_kit/eds/runtime.py) | Lab 6: `Runtime` with a step budget and gated publish (used by the capstone) |
| [`lab_kit/eds/agents/`](lab_kit/eds/agents/) | Lab 7: Academic, Research, Placement, Finance, KPI and Report Generation agents |
| [`lab_kit/eds/graph.py`](lab_kit/eds/graph.py) | Labs 7, 8: `GraphRunner`, parallel domain aggregation, validate-with-self-healing |
| [`lab_kit/eds/validation.py`](lab_kit/eds/validation.py) | Labs 9, 10, 11: the four acceptance checks |
| [`lab_kit/eds/governance.py`](lab_kit/eds/governance.py) | Lab 12: human gate, publish, versioning, metrics, rollback |
| [`lab_kit/eds/specialists.py`](lab_kit/eds/specialists.py) | Lab 13: pluggable KPI packs (NAAC-weighted, NIRF-weighted) |
| [`lab_kit/eds/dashboard.py`](lab_kit/eds/dashboard.py) | Dashboard payload export used by the capstone |
| [`lab_kit/data/stub_data.py`](lab_kit/data/stub_data.py) | Fictional institutional data (departments, placement, research, finance, KPI definitions) |
| [`lab_kit/tests/test_pipeline.py`](lab_kit/tests/test_pipeline.py) | 9 pytest tests over aggregation, KPI synthesis, validation and governance |
| [`lab_kit/labs/`](lab_kit/labs/) | Bridge labs 13 and 14 |

All data is fictional. Swapping `StubConnector` for a connector over real systems would not require changes to the agents.

## How to run

Requires Python 3 (no third-party packages for the scripts).

Run one assignment:

```bash
cd Assignments/Assignment-07_Agentic_Node_Graph
python lab07_node_graph.py
```

Run all twelve assignments and the two bridge labs, stopping at the first failure. This also rewrites each assignment's `output/run_log.txt`:

```bash
cd Assignments
python run_all.py
```

Run the tests (needs `pip install pytest`):

```bash
cd Assignments
python -m pytest lab_kit/tests -q
```

On Windows, if a script prints a `UnicodeEncodeError`, run `set PYTHONIOENCODING=utf-8` (Command Prompt) or `$env:PYTHONIOENCODING="utf-8"` (PowerShell) first. `run_all.py` sets this for the scripts it launches.

## Labs 13 and 14

These are not separate assignment folders. They are covered in two places:

- [`lab_kit/labs/lab13_specialists.py`](lab_kit/labs/lab13_specialists.py): plugs a NAAC-weighted or NIRF-weighted KPI pack into the KPI Agent and shows that only the targets in force change.
- [`lab_kit/labs/lab14_capstone.py`](lab_kit/labs/lab14_capstone.py): one connected run through the governed `Runtime` (connector, graph, parallel agents, validation with self-healing, human approval, versioned publish), writing a dashboard payload, a Markdown decision brief, the audit log and the published record to `lab_kit/out/lab14_capstone/`.
- The course project in [`../Course_Project/`](../Course_Project/) is the full, deployed system. [`../Course_Project/docs/LABS.md`](../Course_Project/docs/LABS.md) maps all 14 labs to their production code and the tests that prove them; each assignment README above ends with its row from that map.
