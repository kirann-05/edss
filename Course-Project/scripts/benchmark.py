"""make benchmark: the four domain agents in parallel against one at a time, on the same graph.

Each domain agent waits a fixed time to stand in for a slow source system. Without that wait the
reads come from memory and take microseconds, so there is nothing for parallelism to win, and the
report says so. "One at a time" is the same graph run with LangGraph's max_concurrency set to 1,
and the run's own events are checked to confirm the agents really did overlap, or really did not.
The report goes to docs/benchmark.md.

Run from backend:  uv run python ../scripts/benchmark.py
"""

import os
import platform
import statistics
import sys
import time
from datetime import date
from pathlib import Path

from acceptance import REF, Bench, plans

from app.services.store import DataStore

LATENCIES = (0.0, 0.25, 0.7, 1.0)  # seconds per domain agent. 0.7 is what the demo uses
REPEATS = 3
REPORT = Path(__file__).resolve().parent.parent / "docs" / "benchmark.md"


def agent_windows(bench: Bench) -> dict[str, tuple[float, float]]:
    """When each domain agent started and finished, from the run's own events."""
    started: dict[str, float] = {}
    finished: dict[str, float] = {}
    for event in bench.events.all(bench.run_id):
        if not event.node.startswith("domain:"):
            continue
        if event.state == "running":
            started[event.node] = event.ts.timestamp()
        elif event.state == "done":
            finished[event.node] = event.ts.timestamp()
    return {node: (started[node], finished[node]) for node in started}


def measure(bench: Bench, plan, sequential: bool) -> tuple[float, float, str]:
    """Milliseconds for the domain phase and for the whole run, and how the agents overlapped."""
    config = {"max_concurrency": 1} if sequential else {}
    began = time.perf_counter()
    bench.run(plan, [], **config)
    whole = (time.perf_counter() - began) * 1000
    windows = sorted(agent_windows(bench).values())
    assert len(windows) == 4, f"expected four domain agents, saw {len(windows)}"
    phase = (max(end for _, end in windows) - min(start for start, _ in windows)) * 1000
    if max(start for start, _ in windows) < min(end for _, end in windows):
        shape = "all four at once"
    elif all(later[0] >= earlier[1] for earlier, later in zip(windows, windows[1:], strict=False)):
        shape = "one at a time"
    else:
        shape = "partly overlapping"
    return phase, whole, shape


def main() -> int:
    store = DataStore.build(REF, 90)
    plan = next(
        p for label, p in plans(store) if label == f"{store.current_period}, all four areas"
    )
    rows = []
    wrong_shape = []
    for latency in LATENCIES:
        bench = Bench(store, latency=latency)
        result: dict[bool, list[tuple[float, float, str]]] = {False: [], True: []}
        for _ in range(REPEATS):
            for sequential in (False, True):
                result[sequential].append(measure(bench, plan, sequential))
        par, seq = result[False], result[True]
        par_phase = statistics.median(p for p, _, _ in par)
        seq_phase = statistics.median(p for p, _, _ in seq)
        par_shapes = {s for _, _, s in par}
        seq_shapes = {s for _, _, s in seq}
        if latency > 0 and (par_shapes != {"all four at once"} or seq_shapes != {"one at a time"}):
            wrong_shape.append(latency)
        rows.append(
            (
                latency, par_phase, seq_phase,
                statistics.median(w for _, w, _ in par), statistics.median(w for _, w, _ in seq),
                ", ".join(sorted(par_shapes)), ", ".join(sorted(seq_shapes)),
            )
        )  # fmt: skip
        print(f"{latency:.2f} s: parallel {par_phase:.0f} ms, one at a time {seq_phase:.0f} ms")

    REPORT.write_text(render(rows))
    print("written to docs/benchmark.md")
    for latency in wrong_shape:
        print(f"  FAIL at {latency} s the agents did not run in the expected shape")
    return 1 if wrong_shape else 0


def render(rows) -> str:
    lines = [
        "# Parallel domain agents: benchmark",
        "",
        f"Written by `make benchmark` on {date.today().isoformat()}, on {platform.machine()} "
        f"({platform.system()}, {os.cpu_count()} cores), Python {platform.python_version()}. "
        f"Median of {REPEATS} runs each. One full run of the graph for the current year with all "
        "four areas, on synthetic data and the canned model.",
        "",
        "**The delay is simulated.** Each domain agent waits the stated time before it reads, to "
        "stand in for a slow university system. The real reads are from memory and take far less "
        "than a millisecond, so the rows below show the shape of parallel work, not how fast the "
        "university's systems are.",
        "",
        "| Delay per agent | Domain phase, parallel | Domain phase, one at a time | Speed-up | "
        "Whole run, parallel | Whole run, one at a time | Agents, parallel | Agents, one at a time |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for latency, par, seq, par_whole, seq_whole, par_shape, seq_shape in rows:
        speedup = f"{seq / par:.1f} times" if par >= 5 else "none to measure"
        lines.append(
            f"| {latency * 1000:.0f} ms | {par:.0f} ms | {seq:.0f} ms | {speedup} "
            f"| {par_whole:.0f} ms | {seq_whole:.0f} ms | {par_shape} | {seq_shape} |"
        )
    lines += [
        "",
        "How to read it: with four agents each waiting the same time, one at a time takes four "
        "waits and in parallel takes one, so the best possible speed-up is four times. With no "
        "delay there is nothing to win, which is why the demo states its simulated delay on screen.",
        "",
        "How it is measured: the domain phase runs from the first agent starting to the last one "
        "finishing, taken from the run's own events. One at a time is the same graph with "
        "LangGraph's `max_concurrency` set to 1, and the events confirm the agents did not overlap.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
