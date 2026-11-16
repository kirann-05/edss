"""
Lab 14 - Capstone: the whole worklet, connected.

Phase: D - Governance & capstone
Goal: integrate everything into a deployed, team-owned system.

    system = deploy(connector, runtime, graph, governance)
    artifact = system.run(request)        # the decision brief
    dashboard.show(artifact, metrics, audit)

This is the connected agentic workflow every earlier lab (1-13) built
one capability of: the MCP-style connector (Lab 5) feeds a governed
runtime (Lab 6) that fans the four domain agents out in parallel
(Lab 8) across the explicit node graph (Lab 7), grounds every figure in
evidence (Lab 9), self-heals on validation failure (Lab 10) behind a
hard acceptance gate (Lab 11), plugs in a domain specialist pack
(Lab 13), and only then reaches the human approval gate and governed,
versioned, rollback-able publish (Lab 12) -- with a full audit trail
and an executive dashboard export at the end.

Run:
    python lab_kit/labs/lab14_capstone.py

Acceptance: the Executive/Leadership produces an approved, validated
decision brief in one session.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from eds.connector import StubConnector
from eds.runtime import Runtime
from eds.governance import HumanGate
from eds.specialists import default_registry
from eds.agents.kpi_agent import KPIAgent
from eds.dashboard import build_dashboard_payload

OUT_DIR = Path(__file__).resolve().parent.parent / "out" / "lab14_capstone"


def deploy(specialist_label: str = "naac_weighted") -> Runtime:
    """system = deploy(connector, runtime, graph, governance)"""
    connector = StubConnector()
    registry = default_registry()
    specialist = registry.get(specialist_label) if specialist_label else None
    kpi_agent = KPIAgent(specialist=specialist)

    runtime = Runtime(
        connector=connector,
        budget=30,
        gates=["publish"],
        checkpoint_dir=OUT_DIR / "checkpoints",
        audit_path=OUT_DIR / "audit_log.jsonl",
        storage_dir=OUT_DIR / "published",
        kpi_agent=kpi_agent,
    )
    return runtime


def main():
    print("=" * 78)
    print("EXECUTIVE DECISION SUPPORT SYSTEM -- LAB 14 CAPSTONE (full connected run)")
    print("=" * 78)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if (OUT_DIR / "audit_log.jsonl").exists():
        (OUT_DIR / "audit_log.jsonl").unlink()

    system = deploy(specialist_label="naac_weighted")

    request = {
        "review_cycle": "Q1 FY26 Governing Council Review",
        "domains": ["academic", "research", "placement", "finance"],
        "requested_by": "Registrar",
    }

    # artifact = system.run(request)
    print("\n[1/4] Running clarify -> plan -> parallel domain aggregation -> KPI synthesis "
          "-> report generation -> validation (with bounded self-healing)...")
    result = system.run_to_draft(request)
    ctx = result.ctx

    print(f"      run_id={ctx.run_id}  domains={list(ctx.domain_results.keys())}  "
          f"attempts={ctx.attempts}  budget_used={result.budget_used}/{result.budget}")
    print(f"      validation passed={result.validation.passed}  failing={result.validation.failing}")
    assert result.validation.passed, "capstone requires a fully validated draft before the human gate"

    kpis = ctx.kpi_result["kpis"]
    below_target = ctx.kpi_result["below_target"]
    print(f"\n[2/4] KPI synthesis: {len(kpis)} KPIs computed, {len(below_target)} below target: "
          f"{below_target}")
    for name, kpi in kpis.items():
        flag = "⚠ BELOW TARGET" if kpi["status"] == "below_target" else "OK"
        print(f"      - {name}: actual={kpi['actual']} target={kpi['target']} "
              f"variance={kpi['variance']}  [{flag}]")

    # The Executive / Leadership gate (Principal/Registrar/Governing Council).
    # This is the one hard stop nothing in this system can route around.
    print("\n[3/4] Executive / Leadership review gate...")
    decision = HumanGate.review(
        ctx.report,
        actor="Dr. A. Sharma",
        role="Registrar",
        decision="approve",
        comment=f"Reviewed {len(kpis)} KPIs ({len(below_target)} flagged below target) "
                f"and {len(ctx.report['options'])} decision option(s). Approved for circulation "
                f"to the Governing Council.",
    )
    print(f"      decision={decision.decision}  actor={decision.actor} ({decision.role})  "
          f"comment='{decision.comment}'")

    version = system.publish(ctx, decision, action="publish")
    print(f"      PUBLISHED as version {version.version} at {version.published_at}")

    # dashboard.show(artifact, metrics, audit)
    print("\n[4/4] Exporting executive dashboard + audit trail...")
    payload = build_dashboard_payload(
        ctx, system.governance, published=version, audit_entries=system.audit.as_list()
    )
    payload_path = OUT_DIR / "dashboard_payload.json"
    payload_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    brief_path = OUT_DIR / "decision_brief.md"
    from eds.skills import format_decision_skill
    doc = format_decision_skill(ctx.report)
    brief_path.write_text(doc.to_markdown(), encoding="utf-8")

    print(f"      dashboard payload -> {payload_path}")
    print(f"      decision brief (markdown) -> {brief_path}")
    print(f"      audit log ({len(system.audit.as_list())} entries) -> "
          f"{OUT_DIR / 'audit_log.jsonl'}")
    print(f"      published record -> {OUT_DIR / 'published'}")

    print("\nACCEPT: the Executive/Leadership produced one approved, validated, versioned "
          "decision brief in a single session -- connector, runtime, node graph, parallel "
          "domain agents, grounding, self-healing, governance and a specialist pack all fired "
          "together as one deployed system.")
    print("=" * 78)


if __name__ == "__main__":
    main()
