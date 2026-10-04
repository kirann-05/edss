"""Lab 13: framework specialists as packs over one implementation, and rule 12 kept."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.graph import GraphDeps, build_graph, initial_state, run_config
from app.agents.llm import FakeLLM
from app.agents.models import BriefDocument, OptionSet, ValidationReport
from app.agents.prompts import build_messages
from app.agents.runtime import RunEvents, Runtime
from app.agents.skills.plan_skill import lock_plan
from app.domain.enums import KpiFramework
from app.governance.audit import AuditLog
from app.governance.service import GovernanceService
from app.specialists import MARKER, PACKS, SPECIALISTS, PackError, load_registry


class Listening(FakeLLM):
    """The canned drafter, remembering what it was told."""

    def __init__(self):
        super().__init__("drafter")
        self.heard = []

    def complete(self, task, payload, schema=None):
        if task == "draft_options":
            self.heard.append(payload)
        return super().complete(task, payload, schema)


@pytest.fixture(scope="module")
def run(connector, plan):
    model, audit = Listening(), AuditLog()
    governance = GovernanceService(audit, lambda doc: ValidationReport(passed=True, checks=()))
    deps = GraphDeps(
        connector=connector, model=model, runtime=Runtime(audit, RunEvents()),
        create_draft=lambda **kw: governance.create_draft(**kw).id, frameworks=SPECIALISTS,
    )  # fmt: skip
    graph = build_graph(deps, InMemorySaver())
    locked = lock_plan(plan, datetime(2026, 10, 3, tzinfo=UTC))
    state = graph.invoke(
        initial_state("run-1", locked, "registrar@edss.test", None), run_config("run-1")
    )
    return state, model


def test_there_is_one_pack_per_framework_and_only_strategic_is_active():
    assert {SPECIALISTS.get(f).framework for f in KpiFramework} == set(KpiFramework)
    assert SPECIALISTS.get(KpiFramework.STRATEGIC).status == "active"
    assert {p.framework for p in SPECIALISTS.pending()} == {KpiFramework.NIRF, KpiFramework.NAAC}
    assert SPECIALISTS.pending_labels() == ("NAAC", "NIRF")


@pytest.mark.parametrize("framework", [KpiFramework.NIRF, KpiFramework.NAAC])
def test_nirf_and_naac_answer_but_hold_nothing_until_iqac_supplies_it(framework, store):
    pack = SPECIALISTS.get(framework)
    assert pack.pending and MARKER in pack.note
    assert pack.guidance == "" and pack.consider == ()
    assert not [d for d in store.definitions if d.framework is framework]  # no invented definition
    with pytest.raises(PackError, match="waits for IQAC"):
        SPECIALISTS.drafting_context(framework)


def test_the_strategic_pack_guides_every_draft_in_a_run(run):
    state, model = run
    guide = SPECIALISTS.drafting_context(KpiFramework.STRATEGIC)
    assert model.heard and all(p["framework"] == guide for p in model.heard)
    sets = [OptionSet.model_validate(s) for s in state["option_sets"].values()]
    assert sets and all(s.framework is KpiFramework.STRATEGIC for s in sets)


def test_every_brief_names_the_packs_still_waiting(run):
    brief = BriefDocument.model_validate(run[0]["brief"])
    (placeholder,) = [a for a in brief.assumptions if a.kind == "placeholder"]
    assert "NAAC and NIRF have no approved definitions yet" in placeholder.text


def test_the_model_is_told_the_guidance_in_words_and_never_a_figure(run):
    _, model = run
    messages = build_messages("draft_options", model.heard[0])
    assert "planning framework" in messages[0]["content"]
    sent = messages[-1]["content"]
    assert "Strategic plan" in sent
    framework = model.heard[0]["framework"]
    assert not any(ch.isdigit() for ch in framework["guidance"] + "".join(framework["consider"]))


def test_a_kpi_tagged_with_a_pending_framework_stops_the_app():
    with pytest.raises(PackError, match="rule 12"):
        SPECIALISTS.check_definitions([KpiFramework.STRATEGIC, KpiFramework.NIRF])
    SPECIALISTS.check_definitions([KpiFramework.STRATEGIC])  # the control


def write_packs(folder: Path, **change):
    for path in PACKS.glob("*.yaml"):
        raw = yaml.safe_load(path.read_text())
        raw.update(change.get(raw["framework"], {}))
        (folder / path.name).write_text(yaml.safe_dump(raw))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            {"NIRF": {"guidance": "Rank higher by publishing more."}},
            "pending pack carries no guidance",
        ),
        ({"NAAC": {"note": "waiting"}}, MARKER),
        ({"NIRF": {"status": "approved"}}, "status must be"),
        ({"STRATEGIC": {"guidance": ""}}, "needs guidance"),
        ({"STRATEGIC": {"consider": ["raise placements by 5 percent"]}}, "words only"),
    ],
)
def test_the_loader_refuses_a_pack_that_breaks_the_rules(tmp_path, change, message):
    write_packs(tmp_path, **change)
    with pytest.raises(PackError, match=message):
        load_registry(tmp_path)


def test_a_missing_pack_is_refused(tmp_path):
    write_packs(tmp_path)
    (tmp_path / "naac.yaml").unlink()
    with pytest.raises(PackError, match="no pack for NAAC"):
        load_registry(tmp_path)
