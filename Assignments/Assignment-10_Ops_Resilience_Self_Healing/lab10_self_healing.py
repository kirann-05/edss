"""
Lab 10 - Ops Resilience: validate, diagnose, fix.

Phase: C - Applied reliability
Goal: make the pipeline self-healing when validation fails.

Run:
    python lab10_self_healing.py

Acceptance: injected faults are detected and fixed within the retry
budget.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from eds.connector import StubConnector
from eds.coordinator import Coordinator
from eds.graph import GraphRunner
from eds.validation import ValidationAgent


def main():
    print("=== Lab 10: inject a fault, watch it get diagnosed and auto-repaired ===\n")
    connector = StubConnector()
    coordinator = Coordinator(max_regenerate_attempts=3)
    graph = GraphRunner(coordinator, connector)

    request = {"review_cycle": "Q1 FY26 (Lab 10 fault-injection demo)",
               "domains": ["academic", "research", "placement", "finance"],
               "requested_by": "Registrar"}
    ctx = coordinator.new_run(request)
    ctx = graph.build_draft(ctx)

    baseline = ValidationAgent.validate(ctx, ctx.plan)
    print(f"Baseline validation (before fault injection): passed={baseline.passed}")
    assert baseline.passed

    # --- inject a fault: strip the assumptions section, exactly the kind
    # --- of thing a flaky generation step could produce -----------------
    print("\nInjecting fault: deleting ctx.report['assumptions'] and ['options'] "
          "(simulates a broken report-generation pass)...")
    ctx.report["assumptions"] = []
    ctx.report["options"] = [{"issue": "no risks listed", "option_a": {"action": "do X"},
                               "option_b": {"action": "do Y"}}]  # missing 'risks' keys too

    faulted = ValidationAgent.validate(ctx, ctx.plan)
    print(f"Post-injection validation: passed={faulted.passed}, failing={faulted.failing}")
    assert not faulted.passed, "fault injection should have broken validation"

    # now let the graph's bounded self-healing loop diagnose and fix it
    report = graph.validate_with_self_healing(ctx)
    print(f"\nAfter self-healing: passed={report.passed}, attempts_used={ctx.attempts}")
    for check, explanation in report.diagnosis.items():
        print(f"  - {check}: {explanation}")

    assert report.passed, "self-healing should repair the injected fault within budget"
    assert ctx.attempts <= coordinator.max_regenerate_attempts

    print(f"\nACCEPT: injected fault was detected and fixed within the retry budget "
          f"({ctx.attempts}/{coordinator.max_regenerate_attempts} attempts used).")


if __name__ == "__main__":
    main()
