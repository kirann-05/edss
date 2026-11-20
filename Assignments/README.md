# The 12 assignments

The course project (EDSS) is divided across the first twelve labs of the Agentic AI build book. Each assignment is the slice of the project that its lab asks for: what was asked, where the code is, how to show it, and the tests that prove it. The code itself lives once, in [`Course-Project/`](../Course-Project/); each assignment links to it.

Labs 13 (discipline-specific specialist packs) and 14 (the integrated, deployed capstone) are the course project as a whole, so they are in `Course-Project/` and described in the [lab map](../Course-Project/docs/LABS.md).

| # | Assignment | Folder | Tests when written |
| --- | --- | --- | --- |
| 1 | Agent vs Chatbot: plan and revise | [Assignment-01-plan-and-revise](Assignment-01-plan-and-revise/README.md) | 73 passed in 7.89s |
| 2 | Tool-Using Agent: call data and compute | [Assignment-02-tool-using-agent](Assignment-02-tool-using-agent/README.md) | 59 passed in 1.15s |
| 3 | Skill Creation: reusable plan and options skills | [Assignment-03-skill-creation](Assignment-03-skill-creation/README.md) | 39 passed in 0.03s |
| 4 | Memory and Retrieval: run state apart from stored memory | [Assignment-04-memory-and-retrieval](Assignment-04-memory-and-retrieval/README.md) | 3 passed, 4 skipped in 0.27s |
| 5 | MCP-Style Connector: one server for all sources | [Assignment-05-mcp-connector](Assignment-05-mcp-connector/README.md) | 39 passed in 2.41s |
| 6 | Runtime: skills, tools, memory and audit under control | [Assignment-06-runtime](Assignment-06-runtime/README.md) | 34 passed, 10 skipped in 0.74s |
| 7 | Agentic Node Graph: the full pipeline | [Assignment-07-agentic-node-graph](Assignment-07-agentic-node-graph/README.md) | 29 passed in 1.13s |
| 8 | Parallel Swarm: fan out, then merge | [Assignment-08-parallel-swarm](Assignment-08-parallel-swarm/README.md) | 29 passed in 1.12s |
| 9 | Deep Research: grounding and evidence | [Assignment-09-grounding-and-evidence](Assignment-09-grounding-and-evidence/README.md) | 38 passed in 0.02s |
| 10 | Ops Resilience: validate, diagnose, fix | [Assignment-10-validate-diagnose-fix](Assignment-10-validate-diagnose-fix/README.md) | 55 passed in 0.09s |
| 11 | SDLC Factory: from a spec to a tested output | [Assignment-11-spec-to-tested-output](Assignment-11-spec-to-tested-output/README.md) | 94 fault trials, 0 problems (`make acceptance`) |
| 12 | Safety and Governance: approval, evaluation, rollback | [Assignment-12-safety-and-governance](Assignment-12-safety-and-governance/README.md) | 73 passed in 0.29s |

Skipped tests (assignments 4 and 6) are the database ones; they run when PostgreSQL is up (`make db-up`, then `make test-db`) and passed there on 27 Oct 2026 (68 database tests).

Back to the [main README](../README.md).
