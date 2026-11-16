"""
Lab 7 - Agentic Node Graph: the full pipeline.

Phase: B - Orchestration
Goal: wire the specialist agents into one explicit graph with state and
branching.

Run:
    python lab07_node_graph.py

Acceptance: one command yields a validated decision-brief draft end to
end.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from eds.connector import StubConnector
from eds.coordinator import Coordinator
from eds.graph import GraphRunner


def main():
    print("=== Lab 7: full node graph, one command -> validated draft ===\n")
    connector = StubConnector()
    coordinator = Coordinator()
    graph = GraphRunner(coordinator, connector)

    request = {"review_cycle": "Q1 FY26 Governing Council review",
               "domains": ["academic", "research", "placement", "finance"],
               "requested_by": "Registrar"}
    ctx = coordinator.new_run(request)

    # graph.chain(ingest -> plan -> workers -> validate)
    ctx = graph.build_draft(ctx)
    report = graph.validate_with_self_healing(ctx)  # graph.edge(validate --fail--> workers) etc.

    print(f"Domains aggregated: {list(ctx.domain_results.keys())}")
    print(f"KPIs synthesized: {list((ctx.kpi_result or {}).get('kpis', {}).keys())}")
    print(f"Report sections: {[s['heading'] for s in (ctx.report or {}).get('sections', [])]}")
    print(f"\nValidation: passed={report.passed}, failing={report.failing}")
    for check, explanation in report.diagnosis.items():
        print(f"  - {check}: {explanation}")

    assert report.passed, "Lab 7 acceptance requires a fully validated end-to-end draft"
    print("\nACCEPT: one call to build_draft() + validate_with_self_healing() produced a "
          "validated decision-brief draft end to end.")


if __name__ == "__main__":
    main()
