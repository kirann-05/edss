"""
Lab 11 - SDLC Factory: spec -> tested output.

Phase: C - Applied reliability
Goal: treat the plan as a spec and the output as a tested
implementation.

Run:
    python lab11_sdlc_factory.py

Acceptance: no decision brief advances to the executive/leadership
without a fully passing acceptance report.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from eds.connector import StubConnector
from eds.coordinator import Coordinator
from eds.graph import GraphRunner
from eds.validation import ValidationAgent


def build(plan, coordinator, connector):
    """artifact = build(plan)  -- a graph run (Lab 7/8/10)."""
    graph = GraphRunner(coordinator, connector)
    ctx = coordinator.new_run(plan)
    ctx = graph.build_draft(ctx)
    return ctx, graph


def acceptance_suite(ctx, plan):
    """report = acceptance_suite(artifact, plan)."""
    return ValidationAgent.validate(ctx, ctx.plan)


def main():
    print("=== Lab 11: 'build' command -- plan in, tested decision brief out ===\n")
    connector = StubConnector()
    coordinator = Coordinator()

    request = {"review_cycle": "Q1 FY26 (Lab 11 build demo)",
               "domains": ["academic", "research", "placement", "finance"],
               "requested_by": "Registrar"}

    ctx, graph = build(request, coordinator, connector)
    report = acceptance_suite(ctx, ctx.plan)

    print(f"Acceptance suite result: all_pass={report.passed}")
    for check, explanation in report.diagnosis.items():
        status = "PASS" if check not in report.failing else "FAIL"
        print(f"  [{status}] {check}: {explanation}")

    # require report.all_pass  -- gate before human review
    if not report.passed:
        print("\nRegenerating via self-healing before allowing advancement...")
        report = graph.validate_with_self_healing(ctx)

    require_all_pass = report.passed
    assert require_all_pass, "Lab 11 gate: no artifact may advance to human review without a green report"

    print(f"\nACCEPT: build() produced a decision-brief artifact with a fully passing "
          f"acceptance report ({len(report.diagnosis)}/{len(report.diagnosis)} checks green) "
          f"-- only now is it eligible for the Executive/Leadership gate.")


if __name__ == "__main__":
    main()
