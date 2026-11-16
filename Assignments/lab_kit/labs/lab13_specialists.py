"""
Lab 13 - Discipline-Specific Agents: domain specialisation.

Phase: D - Governance & capstone
Goal: specialise the worklet to its domain variants.

Run:
    python lab_kit/labs/lab13_specialists.py

Acceptance: specialist outputs use valid domain patterns and produce
checkable results.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eds.connector import StubConnector
from eds.coordinator import Coordinator
from eds.graph import GraphRunner
from eds.agents.kpi_agent import KPIAgent
from eds.specialists import default_registry


def run_with_specialist(label, registry, request):
    connector = StubConnector()
    coordinator = Coordinator()
    specialist = registry.get(label) if label else None
    kpi_agent = KPIAgent(specialist=specialist)
    graph = GraphRunner(coordinator, connector, kpi_agent=kpi_agent)
    ctx = coordinator.new_run(request)
    ctx = graph.build_draft(ctx)
    return ctx


def main():
    print("=== Lab 13: pluggable KPI specialist packs (NAAC-weighted vs NIRF-weighted) ===\n")
    registry = default_registry()
    print(f"Registered specialists: {registry.known()}")

    request = {"review_cycle": "Q1 FY26 (Lab 13 demo)",
               "domains": ["academic", "research", "placement", "finance"],
               "requested_by": "Registrar"}

    ctx_default = run_with_specialist(None, registry, request)
    ctx_naac = run_with_specialist("naac_weighted", registry, request)
    ctx_nirf = run_with_specialist("nirf_weighted", registry, request)

    def targets(ctx, kpi):
        return ctx.kpi_result["kpis"][kpi]["target"]

    print("\ninstitution_pass_percentage target by pack:")
    print(f"  default:        {targets(ctx_default, 'institution_pass_percentage')}")
    print(f"  naac_weighted:  {targets(ctx_naac, 'institution_pass_percentage')}")

    print("\ninstitution_publications_per_faculty target by pack:")
    print(f"  default:        {targets(ctx_default, 'institution_publications_per_faculty')}")
    print(f"  nirf_weighted:  {targets(ctx_nirf, 'institution_publications_per_faculty')}")

    assert targets(ctx_naac, "institution_pass_percentage") == 92.0
    assert targets(ctx_nirf, "institution_publications_per_faculty") == 1.5
    assert targets(ctx_default, "institution_pass_percentage") == 90.0, "default pack unaffected"

    # every specialist output is still checkable: actual/target/variance/status present
    for label, ctx in [("naac_weighted", ctx_naac), ("nirf_weighted", ctx_nirf)]:
        kpi = ctx.kpi_result["kpis"]["institution_pass_percentage"]
        assert {"actual", "target", "variance", "status", "formula", "source_domain"} <= set(kpi.keys()), (
            f"{label} pack produced an unchecked/invalid KPI record")

    print("\nACCEPT: swapping the specialist pack changed only the targets in force; every "
          "output remained a fully checkable KPI record (actual/target/variance/status/source).")


if __name__ == "__main__":
    main()
