"""
Lab 8 - Parallel Swarm: many domain agents, then merge.

Phase: B - Orchestration
Goal: parallelise the per-unit work and select/merge the best.

Run:
    python lab08_parallel_swarm.py

Acceptance: parallel run matches or beats sequential quality at lower
wall-clock time.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from eds.connector import StubConnector
from eds.coordinator import Coordinator
from eds.graph import GraphRunner, DOMAIN_AGENTS
from eds.coordinator import RunContext


class SlowStubConnector(StubConnector):
    """Adds artificial per-read latency so the parallel-vs-sequential
    wall-clock difference is visible in a short demo, standing in for
    real network/API latency to four separate department systems."""

    LATENCY_SECONDS = 0.35

    def _read_department_reports(self, domain=None, **kwargs):
        time.sleep(self.LATENCY_SECONDS)
        return super()._read_department_reports(domain=domain, **kwargs)


def run_sequential(coordinator, connector, ctx):
    graph = GraphRunner(coordinator, connector)
    for domain in ctx.plan.domains:
        if domain not in DOMAIN_AGENTS:
            continue
        agent = DOMAIN_AGENTS[domain]()
        ctx = agent.step(ctx, ctx.plan, connector)
    return ctx


def main():
    print("=== Lab 8: fan-out/fan-in over the 4 domain agents, then merge ===\n")
    request = {"review_cycle": "Q1 FY26 (Lab 8 demo)",
               "domains": ["academic", "research", "placement", "finance"],
               "requested_by": "Registrar"}

    coordinator = Coordinator()
    connector = SlowStubConnector()

    ctx_seq = coordinator.new_run(request)
    t0 = time.perf_counter()
    ctx_seq = run_sequential(coordinator, connector, ctx_seq)
    seq_time = time.perf_counter() - t0

    coordinator2 = Coordinator()
    graph = GraphRunner(coordinator2, connector)
    ctx_par = coordinator2.new_run(request)
    t0 = time.perf_counter()
    ctx_par = graph.run_domain_aggregation(ctx_par)   # results = parallel_map(...)
    par_time = time.perf_counter() - t0

    # merge by plan alignment: every requested domain must be present (coverage == quality here)
    merged_domains = set(ctx_par.domain_results.keys())
    expected_domains = set(d for d in request["domains"] if d in DOMAIN_AGENTS)
    aligned = merged_domains == expected_domains

    print(f"Sequential wall-clock time: {seq_time:.2f}s")
    print(f"Parallel wall-clock time:   {par_time:.2f}s")
    print(f"Speedup: {seq_time / par_time:.2f}x")
    print(f"\nMerge coverage check (alignment_to(plan)): {sorted(merged_domains)} "
          f"== {sorted(expected_domains)} -> {aligned}")
    print(f"Same domain results, both paths agree on academic pass%: "
          f"seq={ctx_seq.domain_results['academic']['institution_pass_percentage']} "
          f"par={ctx_par.domain_results['academic']['institution_pass_percentage']}")

    assert aligned, "merged result must cover exactly the plan's requested domains"
    assert par_time < seq_time, "parallel run should beat sequential wall-clock time"
    assert (ctx_seq.domain_results["academic"]["institution_pass_percentage"]
            == ctx_par.domain_results["academic"]["institution_pass_percentage"]), (
        "parallel and sequential runs must reach identical quality/results")

    print("\nACCEPT: parallel run matched sequential quality at lower wall-clock time.")


if __name__ == "__main__":
    main()
