"""
Lab 12 - Safety & Governance: approval, eval, rollback.

Phase: D - Governance & capstone
Goal: add confidentiality, approval, evaluation and rollback.

Run:
    python lab12_governance.py

Acceptance: only the executive/leadership-approved results publish; any
release rolls back cleanly.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from pathlib import Path
from eds.connector import StubConnector
from eds.coordinator import Coordinator
from eds.graph import GraphRunner
from eds.governance import Governance, HumanGate, UnauthorizedRoleError, ApprovalRequiredError

OUT_DIR = Path(__file__).resolve().parent / "output"


def main():
    print("=== Lab 12: governed release -- approval, versioning, rollback ===\n")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    connector = StubConnector()
    coordinator = Coordinator()
    graph = GraphRunner(coordinator, connector)
    governance = Governance(storage_dir=OUT_DIR / "published")

    request = {"review_cycle": "Q1 FY26 (Lab 12 demo)",
               "domains": ["academic", "research", "placement", "finance"],
               "requested_by": "Registrar"}
    ctx = coordinator.new_run(request)
    ctx = graph.build_draft(ctx)
    validation = graph.validate_with_self_healing(ctx)
    assert validation.passed

    # 1. an unauthorized role must be rejected outright
    try:
        HumanGate.review(ctx.report, actor="Random Staffer", role="Clerk", decision="approve")
        raise AssertionError("expected UnauthorizedRoleError")
    except UnauthorizedRoleError as e:
        print(f"Correctly rejected unauthorized approver: {e}")

    # 2. publishing before approval must be rejected
    try:
        from eds.governance import Decision
        governance.publish(ctx.report, Decision(actor="nobody", role="Registrar", decision="reject"),
                            run_id=ctx.run_id)
        raise AssertionError("expected ApprovalRequiredError")
    except ApprovalRequiredError as e:
        print(f"Correctly rejected publish-without-approval: {e}")

    # 3. a real approval from an authorized role publishes and versions
    decision = HumanGate.review(ctx.report, actor="Dr. A. Sharma", role="Registrar",
                                 decision="approve", comment="Approved for circulation.")
    version_1 = governance.publish(ctx.report, decision, run_id=ctx.run_id)
    governance.record_metric("kpis_below_target",
                              len((ctx.kpi_result or {}).get("below_target", [])), ctx.run_id)
    print(f"\nPublished version {version_1.version} by {version_1.approved_by} ({version_1.role})")

    # 4. an edited approval creates a new version, not a silent overwrite
    decision_edit = HumanGate.review(ctx.report, actor="Principal Rao", role="Principal",
                                      decision="edit",
                                      edits={"leadership_note": "Escalate placement gap to Deans."},
                                      comment="Approved with an added leadership note.")
    version_2 = governance.publish(ctx.report, decision_edit, run_id=ctx.run_id)
    print(f"Published version {version_2.version} (edited) by {version_2.approved_by}")
    assert "leadership_note" in version_2.content

    print(f"\nVersion history: {governance.history()}")

    # 5. one-click rollback
    restored = governance.rollback(to_version=1)
    print(f"\nRolled back to content of v1, recorded as new v{restored.version} "
          f"(restored_from_version={restored.content['restored_from_version']})")
    assert restored.content["restored_from_version"] == 1
    assert "leadership_note" not in restored.content

    print("\nACCEPT: only approved results published; unauthorized/unapproved attempts were "
          "rejected; rollback restored a prior version cleanly.")


if __name__ == "__main__":
    main()
