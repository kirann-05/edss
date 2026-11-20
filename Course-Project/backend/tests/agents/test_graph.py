"""The agent graph end to end, on FakeLLM and the synthetic dataset (Labs 6, 7, 8, 10, 11)."""

import time
from datetime import UTC, date, datetime

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agents.graph import (
    AccessDenied,
    GraphDeps,
    PlanNotLocked,
    build_graph,
    initial_state,
    run_config,
)
from app.agents.llm import FakeLLM
from app.agents.models import BriefDocument, ValidationReport
from app.agents.runtime import RunEvents, Runtime
from app.agents.skills.plan_skill import lock_plan
from app.agents.validation.checks import ValidationContext
from app.agents.validation.faults import FAULTS
from app.agents.validation.suite import validate
from app.domain.enums import BriefStatus, Domain
from app.governance.audit import AuditLog
from app.governance.service import GovernanceService
from app.services.connector import InMemoryConnector, ScopeRegistry

REF = date(2026, 10, 1)


class StubbornModel(FakeLLM):
    """A model that writes a figure by hand on every attempt, however many times it is told not to."""

    def complete(self, task, payload, schema=None):
        return super().complete(task, {**payload, "attempt": 1, "inject": ["fake_number"]})


class Harness:
    def __init__(self, store, *, model=None, source_latency=0.0, max_attempts=3):
        self.audit = AuditLog()
        self.events = RunEvents()
        self.runtime = Runtime(self.audit, self.events)
        self.scopes = ScopeRegistry(REF)
        self.connector = InMemoryConnector(store, self.scopes)
        self.store = store

        def validator(doc: BriefDocument) -> ValidationReport:
            return validate(doc, self.context)

        self.governance = GovernanceService(self.audit, validator)
        self.context = ValidationContext(
            plan=None,  # filled in by run()
            facts=store.facts_by_id,
            sources=store.sources,
            publications=tuple(self.connector.get_publications(store.current_period)),
            definitions={d.key: d for d in store.definitions},
        )
        deps = GraphDeps(
            connector=self.connector,
            model=model or FakeLLM("drafter"),
            runtime=self.runtime,
            create_draft=lambda **kw: self.governance.create_draft(**kw).id,
            max_attempts=max_attempts,
            source_latency=source_latency,
        )
        self.checkpointer = InMemorySaver()
        self.graph = build_graph(deps, self.checkpointer)

    def run(self, plan, *, faults=None, run_id="run-1", locked=True, resume=None):
        if locked and not plan.locked:
            plan = lock_plan(plan, datetime(2026, 10, 3, tzinfo=UTC))
        self.context = ValidationContext(**{**self.context.__dict__, "plan": plan})
        config = run_config(run_id)
        if resume == "none":
            return self.graph.invoke(None, config)
        return self.graph.invoke(initial_state(run_id, plan, "registrar@edss.test", faults), config)

    def state(self, run_id="run-1"):
        return self.graph.get_state(run_config(run_id))


@pytest.fixture
def harness(store):
    return Harness(store)


def waiting_for_a_person(result):
    return "__interrupt__" in result


class TestHappyPath:
    def test_the_run_stops_at_the_human_gate_with_a_validated_draft(self, harness, plan):
        result = harness.run(plan)
        assert waiting_for_a_person(result)
        assert harness.state().next == ("human_gate",)
        assert result["attempts"] == 1 and result["escalated"] is False
        report = ValidationReport.model_validate(result["validation"])
        assert report.passed
        (draft,) = harness.governance.briefs()
        assert draft.status is BriefStatus.DRAFT and draft.id == result["brief_id"]

    def test_every_kpi_in_the_locked_plan_is_in_the_brief_and_off_target_ones_have_options(
        self, harness, plan
    ):
        result = harness.run(plan)
        document = BriefDocument.model_validate(result["brief"])
        assert {k.key for k in document.kpis} == set(plan.kpi_keys)
        assert {s.kpi_key for s in document.option_sets} == {"PL_PCT", "RS_PUB_PF", "AC_PASS_PCT"}

    def test_the_figures_in_the_brief_come_from_the_engine_not_the_model(
        self, harness, plan, store
    ):
        result = harness.run(plan)
        by_key = {f["key"]: f for f in result["figures"]}
        assert by_key["PL_PCT"]["value"] == str(store.result("PL_PCT", store.current_period).value)
        assert by_key["PL_PCT"]["status"] == "missed"

    def test_nothing_is_published_until_a_person_decides(self, harness, plan):
        harness.run(plan)
        assert harness.governance.current() is None
        assert not hasattr(harness.graph, "publish")

    def test_a_person_resuming_the_gate_lets_the_run_finish(self, harness, plan):
        harness.run(plan)
        config = run_config("run-1")
        final = harness.graph.invoke(Command(resume={"status": "published", "version": 1}), config)
        assert final["status"] == "completed" and final["published_version"] == 1
        assert not waiting_for_a_person(final)


class TestParallelism:
    def test_the_four_domain_agents_run_at_the_same_time(self, store, plan):
        harness = Harness(store, source_latency=0.25)
        harness.run(plan)
        events = harness.events.all("run-1")
        domain = [(i, e) for i, e in enumerate(events) if e.node.startswith("domain:")]
        running = [i for i, e in domain if e.state == "running"]
        done = [i for i, e in domain if e.state == "done"]
        assert len(running) == len(done) == 4
        assert max(running) < min(done)  # all four were under way before any finished

    def test_parallel_beats_sequential_on_wall_clock(self, store, plan):
        harness = Harness(store, source_latency=0.25)
        started = time.monotonic()
        harness.run(plan)
        assert (
            time.monotonic() - started < 0.9
        )  # four sequential 0.25 second reads alone take one second

    def test_the_join_waits_for_every_agent(self, harness, plan):
        result = harness.run(plan)
        assert set(result["domain_views"]) == {"academic", "research", "placement", "finance"}
        assert result["facts"]  # the synthesis saw all of them


class TestFailureInjectionThroughTheGraph:
    @pytest.mark.parametrize("fault", FAULTS)
    def test_every_fault_is_detected_and_repaired_inside_the_budget(self, harness, plan, fault):
        result = harness.run(plan, faults=[fault])
        reports = [ValidationReport.model_validate(r) for r in result["reports"]]
        assert not reports[0].passed, f"{fault} was not detected"
        assert reports[-1].passed, f"{fault} was not repaired"
        assert len(reports) <= 3
        assert result["escalated"] is False
        assert result["repair_log"]

    def test_only_the_failing_part_is_repaired(self, harness, plan):
        result = harness.run(plan, faults=["fake_number"])
        log = result["repair_log"]
        assert len(log) == 1 and log[0].startswith("Regenerated options for")

    def test_the_repaired_draft_waits_for_a_person_like_any_other(self, harness, plan):
        result = harness.run(plan, faults=["rounded_miss"])
        assert waiting_for_a_person(result)
        assert harness.governance.briefs()[0].attempts == 2


class TestEscalation:
    def test_when_repair_cannot_fix_it_the_draft_is_escalated_to_a_person_with_the_diagnosis(
        self, store, plan
    ):
        harness = Harness(store, model=StubbornModel("drafter"))
        result = harness.run(plan, faults=["fake_number"])
        assert result["attempts"] == 3  # the budget, never a fourth look
        assert result["escalated"] is True
        assert waiting_for_a_person(result)  # still reaches the human gate
        (draft,) = harness.governance.briefs()
        assert draft.status is BriefStatus.ESCALATED
        assert draft.diagnosis and "12" in draft.diagnosis

    def test_the_budget_is_configurable(self, store, plan):
        harness = Harness(store, model=StubbornModel("drafter"), max_attempts=2)
        assert harness.run(plan, faults=["fake_number"])["attempts"] == 2


class TestAudit:
    def test_every_step_leaves_a_row_with_its_inputs_and_outputs(self, harness, plan):
        harness.run(plan)
        rows = harness.audit.rows(run_id="run-1", action="node.done")
        actors = {r.actor_id for r in rows}
        assert {
            "plan_lock",
            "access_check",
            "kpi_synthesis",
            "report_compose",
            "validate",
            "prepare_gate",
        } <= actors
        assert {
            "domain:academic",
            "domain:research",
            "domain:placement",
            "domain:finance",
        } <= actors
        assert {"options:PL_PCT", "options:RS_PUB_PF", "options:AC_PASS_PCT"} <= actors
        for row in rows:
            assert row.inputs["keys"] and row.inputs["digest"]
            assert row.outputs["digest"] and "summary" in row.outputs

    def test_the_whole_chain_verifies(self, harness, plan):
        harness.run(plan, faults=["fake_number"])
        result = harness.audit.verify()
        assert result.ok and result.checked > 10

    def test_a_row_digest_changes_if_the_content_changes(self, store, plan):
        a, b = Harness(store), Harness(store)
        a.run(plan)
        b.run(plan, faults=["fake_number"])

        def digest(h):
            row = next(
                r for r in h.audit.rows(action="node.done") if r.actor_id == "report_compose"
            )
            return row.outputs["digest"]

        assert digest(a) != digest(b)


class TestResilience:
    def test_a_crashed_run_resumes_from_its_last_checkpoint_without_redoing_finished_work(
        self, harness, plan
    ):
        harness.runtime.crash_once("kpi_synthesis")
        with pytest.raises(RuntimeError, match="stopped unexpectedly"):
            harness.run(plan)
        assert harness.state().next == ("kpi_synthesis",)

        result = harness.run(
            plan, resume="none"
        )  # resume: no new input, continue from the checkpoint
        assert waiting_for_a_person(result)

        done = [r.actor_id for r in harness.audit.rows(run_id="run-1", action="node.done")]
        assert sum(1 for a in done if a.startswith("domain:")) == 4  # not run a second time
        assert done.count("access_check") == 1
        assert [r.actor_id for r in harness.audit.rows(action="node.failed")] == ["kpi_synthesis"]

    def test_a_run_over_its_time_budget_is_stopped(self, store, plan):
        harness = Harness(store)
        harness.runtime.budget_seconds = 0.0
        with pytest.raises(Exception, match="seconds"):
            harness.run(plan)


class TestGuards:
    def test_an_unlocked_plan_cannot_start_a_run(self, harness, plan):
        with pytest.raises(PlanNotLocked):
            harness.run(plan, locked=False)

    def test_a_domain_without_a_registrar_authorised_scope_stops_the_run_before_any_data_is_read(
        self, harness, plan
    ):
        harness.scopes.revoke(Domain.FINANCE)
        with pytest.raises(AccessDenied, match="Finance"):
            harness.run(plan)
        assert harness.governance.briefs() == []
        assert not [e for e in harness.events.all("run-1") if e.node.startswith("domain:")]
        assert harness.audit.rows(action="node.failed")

    def test_a_plan_that_only_covers_some_domains_needs_only_those_scopes(self, harness, plan):
        harness.scopes.revoke(Domain.FINANCE)
        narrower = plan.model_copy(
            update={
                "domains": (Domain.ACADEMIC,),
                "kpi_keys": tuple(k for k in plan.kpi_keys if k.startswith("AC_")),
            }
        )
        assert waiting_for_a_person(harness.run(narrower))

    def test_no_external_tracing_is_active_during_a_run(self, harness, plan):
        import os

        from app.core.tracing import TRACING_VARS, enforce_no_external_tracing

        enforce_no_external_tracing()
        harness.run(plan)
        assert all(os.environ[v] == "false" for v in TRACING_VARS)
        try:
            from langsmith.utils import tracing_is_enabled
        except ImportError:  # pragma: no cover
            return
        assert tracing_is_enabled() is False
