# Assignment 8: Parallel Swarm (many domain agents, then merge)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: B, Orchestration

## Objective

Parallelise the per-unit work and select the best. Several worker agents run at the same time and a merge step combines their results according to the plan, cutting latency without losing quality. The book's pitfall: merge strictly by plan alignment; picking the "nicest" output quietly breaks coverage.

## Concept applied in EDSS

The four domain agents (Academic, Research, Placement, Finance) read from four separate department systems and do not depend on each other, so they can run in parallel. The merge waits for all four before KPI synthesis starts. "Quality" here means coverage and correctness: the merged result must contain exactly the domains the plan asked for, and must give the same figures as a sequential run. EDSS does not do best-of-N text selection, because KPI arithmetic has one right answer.

## Technical stack

- Python 3, standard library only (`concurrent.futures.ThreadPoolExecutor`, `time.perf_counter`)
- [`eds/graph.py`](../lab_kit/eds/graph.py): `GraphRunner.run_domain_aggregation`, `DOMAIN_AGENTS`

## Implementation

Script: [`lab08_parallel_swarm.py`](lab08_parallel_swarm.py)

1. Defines `SlowStubConnector`, a subclass of `StubConnector` that sleeps 0.35 s on every department-report read. This stands in for network latency to four department systems, so the time difference is visible.
2. Sequential path: `run_sequential()` loops over the plan's domains and calls each domain agent's `step()` one after another. Timed with `perf_counter`.
3. Parallel path: `GraphRunner.run_domain_aggregation()` submits one job per domain to a thread pool (`max_workers=4`). Each worker runs on its own isolated `RunContext` copy and writes only its own `domain_results[domain]` key; the merge copies each finished domain back onto the shared context and writes an audit entry.
4. Merge check (`alignment_to(plan)`): the set of merged domains must equal the set of requested domains.
5. Asserts the merge is aligned, the parallel time is lower, and both paths report the same academic pass percentage.

Key pieces:

| Name | File | Role |
| --- | --- | --- |
| `GraphRunner.run_domain_aggregation` | [`graph.py`](../lab_kit/eds/graph.py) | Fan-out with `ThreadPoolExecutor`, fan-in with `as_completed` |
| `GraphRunner._run_one_domain` | [`graph.py`](../lab_kit/eds/graph.py) | Runs one agent on an isolated context copy |
| `DOMAIN_AGENTS` | [`graph.py`](../lab_kit/eds/graph.py) | Maps domain names to agent classes |

## How to run

```bash
cd Assignments/Assignment-08_Parallel_Swarm
python lab08_parallel_swarm.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first. Timings vary from machine to machine.

## Result / evidence

Acceptance (book): the parallel run matches or beats sequential quality at lower wall-clock time.

From [`output/run_log.txt`](output/run_log.txt):

```
Sequential wall-clock time: 1.40s
Parallel wall-clock time:   0.36s
Speedup: 3.88x

Merge coverage check (alignment_to(plan)): ['academic', 'finance', 'placement', 'research'] == ['academic', 'finance', 'placement', 'research'] -> True
Same domain results, both paths agree on academic pass%: seq=87.1 par=87.1

ACCEPT: parallel run matched sequential quality at lower wall-clock time.
```

With four reads of 0.35 s each, the sequential run takes about 4 x 0.35 s and the parallel run about one read's worth, which is what the 3.88x speedup shows. Note that the quality comparison in the script checks one figure (academic pass percentage) plus domain coverage.

## In the full system

| | |
| --- | --- |
| Production code | LangGraph `Send` fan-out to the four domain agents and to option drafting, in [`app/agents/graph.py`](../../Course_Project/backend/app/agents/graph.py) |
| What it does there | The run page reports "4 domain agents worked at the same time (measured from the events)"; `make benchmark` measures it |
| Proved by | [`tests/agents/test_graph.py`](../../Course_Project/backend/tests/agents/test_graph.py) (`TestParallelism`), [`docs/benchmark.md`](../../Course_Project/docs/benchmark.md) |

The course project documents this reading of the book in [`docs/SPEC.md`](../../Course_Project/docs/SPEC.md) section 9: best-of-N merging suits generated text, not KPI arithmetic, so the merge is by plan coverage.
