"""make acceptance: every injected fault, over every period and mix of areas, through the real graph.

For each plan it runs one clean draft, then each of the eight faults (docs/ARCHITECTURE.md section
10), and records whether the first validation caught it, whether the check meant to catch it did,
whether the repair cleared it inside the retry budget, and what else failed. A fault with nothing to
act on in a plan (a double-counted paper in a plan with no research KPI) is counted as not
applicable, never as a pass. It then runs a model that ignores every diagnosis, to show the budget
holds. The report goes to docs/acceptance-report.md, and the command fails on any miss.

Run from backend:  uv run python ../scripts/acceptance.py
Synthetic data and the canned model only, so the numbers are the same on every run.
"""

import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from app.agents.graph import GraphDeps, build_graph, initial_state, run_config
from app.agents.llm import FakeLLM
from app.agents.models import BriefDocument, Plan, ValidationReport
from app.agents.runtime import RunEvents, Runtime
from app.agents.skills.plan_skill import lock_plan
from app.agents.validation.checks import ValidationContext
from app.agents.validation.faults import CAUGHT_BY, FAULT_INFO, FAULTS, apply_fault
from app.domain.enums import Domain
from app.domain.models import MetricFact
from app.governance.audit import AuditLog
from app.governance.service import GovernanceService
from app.services.connector import InMemoryConnector, ScopeRegistry
from app.services.store import DataStore

REF = date(2026, 10, 1)  # a fixed day, so freshness and the report never drift
MAX_ATTEMPTS = 3
REPORT = Path(__file__).resolve().parent.parent / "docs" / "acceptance-report.md"
AREAS = (Domain.ACADEMIC, Domain.RESEARCH, Domain.PLACEMENT, Domain.FINANCE)
AREA_MIXES: tuple[tuple[Domain, ...], ...] = (
    AREAS,
    (Domain.ACADEMIC,),
    (Domain.RESEARCH,),
    (Domain.PLACEMENT,),
    (Domain.FINANCE,),
    (Domain.PLACEMENT, Domain.RESEARCH),
)
# a figure that lost its sources is also seen by V1, because a headline token points at it
ALSO_EXPECTED = {"dropped_source": frozenset({"V1"})}


class StubbornModel(FakeLLM):
    """Writes a figure by hand on every attempt, however often it is told not to."""

    def complete(self, task, payload, schema=None):
        return super().complete(task, {**payload, "attempt": 1, "inject": ["fake_number"]})


@dataclass
class Trial:
    plan: str
    fault: str
    applies: bool
    why_not: str = ""
    first_failing: frozenset[str] = frozenset()
    repaired: bool = False
    attempts: int = 0
    escalated: bool = False

    @property
    def detected(self) -> bool:
        return bool(self.first_failing)

    @property
    def by_intended(self) -> bool:
        return CAUGHT_BY[self.fault] <= self.first_failing

    @property
    def unrelated(self) -> frozenset[str]:
        return (
            self.first_failing - CAUGHT_BY[self.fault] - ALSO_EXPECTED.get(self.fault, frozenset())
        )

    @property
    def ok(self) -> bool:
        return (
            self.detected and self.by_intended and not self.unrelated and self.repaired
            and self.attempts <= MAX_ATTEMPTS and not self.escalated
        )  # fmt: skip


@dataclass
class Bench:
    store: DataStore
    model: FakeLLM = field(default_factory=lambda: FakeLLM("drafter"))
    count: int = 0

    def __post_init__(self) -> None:
        self.connector = InMemoryConnector(self.store, ScopeRegistry(REF))
        audit = AuditLog()
        # its validator only runs on a person's decision, which this script never makes
        governance = GovernanceService(audit, lambda doc: ValidationReport(passed=True, checks=()))
        deps = GraphDeps(
            connector=self.connector,
            model=self.model,
            runtime=Runtime(audit, RunEvents()),
            create_draft=lambda **kw: governance.create_draft(**kw).id,
            max_attempts=MAX_ATTEMPTS,
        )
        self.graph = build_graph(deps, InMemorySaver())

    def run(self, plan: Plan, faults: list[str]) -> dict[str, Any]:
        self.count += 1
        run_id = f"acceptance-{self.count}"
        locked = lock_plan(plan, datetime(2026, 10, 3, tzinfo=UTC))
        return self.graph.invoke(
            initial_state(run_id, locked, "registrar@edss.test", faults), run_config(run_id)
        )

    def context(self, plan: Plan, state: dict[str, Any]) -> ValidationContext:
        facts = {f["id"]: MetricFact.model_validate(f) for f in state.get("facts", [])}
        return ValidationContext(
            plan=plan,
            facts=facts,
            sources=self.store.sources,
            publications=tuple(self.connector.get_publications(plan.period_year)),
            definitions={d.key: d for d in self.store.definitions},
        )


def reports_of(state: dict[str, Any]) -> list[ValidationReport]:
    return [ValidationReport.model_validate(r) for r in state["reports"]]


def failing(report: ValidationReport) -> frozenset[str]:
    return frozenset(c.id for c in report.checks if not c.passed)


def plans(store: DataStore) -> list[tuple[str, Plan]]:
    out = []
    for period in store.periods:
        for areas in AREA_MIXES:
            keys = tuple(d.key for d in store.definitions if d.domain in areas)
            label = "all four areas" if len(areas) == 4 else " and ".join(a.value for a in areas)
            plan = Plan(
                request=f"Acceptance: {label}, {period}", period_year=period, domains=areas,
                kpi_keys=keys, options_for="off_target", audience="Internal leadership review",
                steps=(),
            )  # fmt: skip
            out.append((f"{period}, {label}", plan))
    return out


def applicability(fault: str, clean: BriefDocument, context: ValidationContext) -> str:
    """Empty if the fault has something to break in this draft, otherwise why not."""
    try:
        broken = apply_fault(clean, fault, context)
    except (StopIteration, IndexError):
        return "nothing in this plan for it to act on"
    if broken.model_dump() == clean.model_dump():
        return "it changes nothing in this plan"
    return ""


def main() -> int:
    started = time.monotonic()
    store = DataStore.build(REF, 90)
    bench = Bench(store)
    clean_results: list[tuple[str, bool]] = []
    trials: list[Trial] = []

    for label, plan in plans(store):
        state = bench.run(plan, [])
        reports = reports_of(state)
        clean_results.append((label, len(reports) == 1 and reports[0].passed))
        clean = BriefDocument.model_validate(state["brief"])
        context = bench.context(plan, state)
        for fault in FAULTS:
            why_not = applicability(fault, clean, context)
            if why_not:
                trials.append(Trial(label, fault, applies=False, why_not=why_not))
                continue
            result = bench.run(plan, [fault])
            reports = reports_of(result)
            trials.append(
                Trial(
                    label, fault, applies=True, first_failing=failing(reports[0]),
                    repaired=reports[-1].passed, attempts=len(reports),
                    escalated=bool(result.get("escalated")),
                )
            )  # fmt: skip

    # the budget: a model that ignores the diagnosis is stopped, and a person gets the draft
    stubborn = Bench(store, model=StubbornModel("drafter"))
    label, plan = plans(store)[0]
    budget_state = stubborn.run(plan, ["fake_number"])
    budget_ok = budget_state["attempts"] == MAX_ATTEMPTS and budget_state["escalated"] is True

    elapsed = time.monotonic() - started
    text = render(
        trials, clean_results, budget_state, budget_ok, bench.count + stubborn.count, elapsed
    )
    REPORT.write_text(text)

    applied = [t for t in trials if t.applies]
    problems = [t for t in applied if not t.ok]
    missing = [f for f in FAULTS if not any(t.fault == f for t in applied)]
    clean_failed = [label for label, ok in clean_results if not ok]
    print(
        f"{len(applied)} fault trials, {len(problems)} problems, written to docs/acceptance-report.md"
    )
    for t in problems:
        print(
            f"  FAIL {t.fault} on {t.plan}: failing {sorted(t.first_failing)}, repaired {t.repaired}"
        )
    for f in missing:
        print(f"  FAIL {f} never applied to any plan, so it was not measured")
    for label in clean_failed:
        print(f"  FAIL the clean draft for {label} did not pass first time")
    if not budget_ok:
        print("  FAIL the retry budget did not stop a model that ignores the diagnosis")
    return 1 if problems or missing or clean_failed or not budget_ok else 0


def pct(part: int, whole: int) -> str:
    return f"{part} of {whole} ({100 * part / whole:.0f} percent)" if whole else "none"


def render(
    trials: list[Trial],
    clean_results: list[tuple[str, bool]],
    budget_state: dict[str, Any],
    budget_ok: bool,
    runs: int,
    elapsed: float,
) -> str:
    applied = [t for t in trials if t.applies]
    skipped = [t for t in trials if not t.applies]
    clean_passed = sum(ok for _, ok in clean_results)
    lines = [
        "# Acceptance report",
        "",
        f"Written by `make acceptance` on {date.today().isoformat()}. Synthetic data (reference day "
        f"{REF.isoformat()}) and the canned model, so the same code gives the same numbers. "
        f"{len(clean_results)} plans: every period, each with all four areas, each area alone, and "
        f"placement with research. {runs} graph runs in {elapsed:.1f} seconds.",
        "",
        "## Summary",
        "",
        "| Measure | Result |",
        "| --- | --- |",
        f"| Clean drafts that passed all nine checks first time | {pct(clean_passed, len(clean_results))} |",
        f"| Fault trials (a fault that had something to break) | {len(applied)} |",
        f"| Caught on the first attempt | {pct(sum(t.detected for t in applied), len(applied))} |",
        f"| Caught by the check meant to catch it | {pct(sum(t.by_intended for t in applied), len(applied))} |",
        f"| Also failed an unrelated check | {pct(sum(bool(t.unrelated) for t in applied), len(applied))} |",
        f"| Repaired inside the budget of {MAX_ATTEMPTS} attempts | {pct(sum(t.repaired for t in applied), len(applied))} |",
        f"| Escalated to a person | {sum(t.escalated for t in applied)} |",
        f"| Not applicable to the plan | {len(skipped)}, listed below, not counted as passes |",
        "",
        "## By fault",
        "",
        "| Fault | What it does | Meant to be caught by | Trials | Caught | By that check | Repaired | Attempts used |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for fault in FAULTS:
        ts = [t for t in applied if t.fault == fault]
        name, what = FAULT_INFO[fault]
        attempts = sorted({t.attempts for t in ts})
        lines.append(
            f"| {name} | {what} | {', '.join(sorted(CAUGHT_BY[fault]))} | {len(ts)} "
            f"| {sum(t.detected for t in ts)} | {sum(t.by_intended for t in ts)} "
            f"| {sum(t.repaired for t in ts)} | {', '.join(map(str, attempts)) or 'none'} |"
        )
    lines += [
        "",
        "## The retry budget",
        "",
        "A model that writes a figure by hand on every attempt, whatever the diagnosis says, is "
        f"stopped after {budget_state['attempts']} attempts and the draft goes to a person "
        f"{'escalated' if budget_state['escalated'] else 'NOT escalated'}, with the diagnosis. "
        f"{'As required.' if budget_ok else 'This is a failure.'}",
        "",
        "## Not applicable, and why",
        "",
    ]
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for t in skipped:
        grouped[(t.fault, t.why_not)].append(t.plan)
    if not grouped:
        lines.append("None.")
    for (fault, why), where in sorted(grouped.items()):
        lines.append(f"- {FAULT_INFO[fault][0]}: {why}, in {len(where)} plans ({'; '.join(where)})")
    lines += [
        "",
        "## What this does not show",
        "",
        "- The repairs here are by the canned model, which follows the diagnosis. How often a real "
        "model repairs a draft is not measured: in `docs/evals` the local model never needed a repair.",
        "- The eight faults are the ones we wrote. A model can fail in ways that are not on the list, "
        "which is why a person reviews every draft.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
