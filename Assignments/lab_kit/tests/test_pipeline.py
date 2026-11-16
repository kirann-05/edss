import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eds.connector import StubConnector
from eds.coordinator import Coordinator
from eds.graph import GraphRunner
from eds.validation import ValidationAgent
from eds.governance import Governance, HumanGate, ApprovalRequiredError, UnauthorizedRoleError


def _fresh_run(domains=None):
    connector = StubConnector()
    coordinator = Coordinator()
    graph = GraphRunner(coordinator, connector)
    request = {"review_cycle": "pytest run", "domains": domains or
               ["academic", "research", "placement", "finance"], "requested_by": "Registrar"}
    ctx = coordinator.new_run(request)
    ctx = graph.build_draft(ctx)
    return ctx, graph


def test_all_four_domains_aggregate():
    ctx, _ = _fresh_run()
    assert set(ctx.domain_results.keys()) == {"academic", "research", "placement", "finance"}


def test_placement_excludes_provisional_offers():
    ctx, _ = _fresh_run()
    placement = ctx.domain_results["placement"]
    # 162+109+78+51 = 400 confirmed placed; provisional offers must not be folded in
    assert placement["provisional_offers_excluded_from_placed"] == 6 + 4 + 3 + 2
    assert placement["institution_placement_percentage"] < 100


def test_research_notes_cross_department_collaboration_without_double_counting():
    ctx, _ = _fresh_run()
    research = ctx.domain_results["research"]
    # CS (42) + ECE (27) + MECH (19) + CIVIL (14) = 102, counted once each despite the shared collab id
    assert research["institution_publications_total"] == 42 + 27 + 19 + 14


def test_kpi_synthesis_produces_variance_for_every_kpi():
    ctx, _ = _fresh_run()
    from eds.agents.kpi_agent import KPIAgent
    from eds.coordinator import Coordinator as C
    from eds.connector import StubConnector as SC
    connector = SC()
    coordinator = C()
    graph = GraphRunner(coordinator, connector, kpi_agent=KPIAgent())
    ctx2 = coordinator.new_run({"review_cycle": "pytest kpi", "requested_by": "Registrar"})
    ctx2 = graph.build_draft(ctx2)
    for name, kpi in ctx2.kpi_result["kpis"].items():
        assert {"actual", "target", "variance", "status", "formula", "framework", "source_domain"} <= set(kpi)


def test_validation_passes_on_a_clean_draft():
    ctx, graph = _fresh_run()
    report = ValidationAgent.validate(ctx, ctx.plan)
    assert report.passed, report.diagnosis


def test_validation_fails_when_a_domain_drops_its_evidence():
    ctx, _ = _fresh_run()
    del ctx.domain_results["finance"]["evidence"]
    report = ValidationAgent.validate(ctx, ctx.plan)
    assert not report.passed
    assert "every figure cites its source" in report.failing


def test_governance_rejects_unapproved_publish():
    ctx, _ = _fresh_run()
    governance = Governance()
    decision = HumanGate.review(ctx.report, actor="X", role="Registrar", decision="reject")
    try:
        governance.publish(ctx.report, decision, run_id=ctx.run_id)
        assert False, "expected ApprovalRequiredError"
    except ApprovalRequiredError:
        pass


def test_governance_rejects_unauthorized_role():
    ctx, _ = _fresh_run()
    try:
        HumanGate.review(ctx.report, actor="X", role="Random Person", decision="approve")
        assert False, "expected UnauthorizedRoleError"
    except UnauthorizedRoleError:
        pass


def test_rollback_restores_prior_version_content():
    ctx, _ = _fresh_run()
    governance = Governance()
    d1 = HumanGate.review(ctx.report, actor="A", role="Registrar", decision="approve")
    v1 = governance.publish(ctx.report, d1, run_id=ctx.run_id)
    d2 = HumanGate.review(ctx.report, actor="B", role="Principal", decision="edit",
                           edits={"extra_note": "added later"})
    governance.publish(ctx.report, d2, run_id=ctx.run_id)
    restored = governance.rollback(to_version=v1.version)
    assert "extra_note" not in restored.content
    assert restored.content["restored_from_version"] == v1.version
