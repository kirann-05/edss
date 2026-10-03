"""How reliable is a model at the narrow jobs this system gives it? Measured, not claimed.

Run it from the backend folder:

    uv run python ../scripts/evaluate_llm.py --provider ollama --model qwen3.5:4b --trials 5
    uv run python ../scripts/evaluate_llm.py --provider fake          # the rule-based baseline

Two things are measured, on synthetic data only:

1. The planner. Ten requests with the answer a sensible person would give written beside them: what
   still needs asking, and what the plan should be (period, areas, audience, options scope). The same
   cases are run through the rule-based FakeLLM, so a model's score can be read against a baseline
   that costs nothing.
2. The drafter. Option text for every off-target KPI, several times with different seeds, composed into
   a brief and put through the real validation gate (V1 to V9). This is the number that matters: how
   often does a draft pass the gate with no help, how often after the model is told what was wrong,
   and how often not at all.

The labels are my reading of the requests, not ground truth from the university. Results go to
docs/evals as Markdown and JSON, with the settings that produced them.
"""

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from app.agents.compose import compose_brief, figure_from, off_target, trend_word
from app.agents.llm import LLMOutputError, LlmSettings, LLMUnavailable, ModelStats, get_chat_model
from app.agents.models import Plan
from app.agents.skills.options_skill import draft_option_set
from app.agents.skills.plan_skill import AUDIENCES, KpiInfo, PlanCatalogue, clarify, propose_plan
from app.agents.validation.suite import validate
from app.domain.enums import Domain
from app.services.connector import InMemoryConnector, ScopeRegistry
from app.services.store import DataStore
from app.services.system_config import SystemConfig
from app.services.validation_context import context_for_document

COUNCIL, INTERNAL = AUDIENCES


@dataclass(frozen=True)
class Case:
    request: str
    ask: frozenset[str]  # what still needs asking
    # what the plan should be once everything is known. None means: do not score the plan
    domains: frozenset[str] | None = None
    period: str | None = None  # "current" means the catalogue's current period
    audience: str | None = None
    options_for: str | None = None


ALL = frozenset({"academic", "research", "placement", "finance"})
CASES = [
    Case("Prepare the leadership brief", frozenset({"period", "scope", "audience"})),
    Case("How are we doing?", frozenset({"period", "scope", "audience"})),
    Case(
        "Where did we miss target this year, and what should we do about it?",
        frozenset({"scope", "audience"}),
    ),
    Case("Prepare the placement brief", frozenset({"period", "audience"})),
    Case(
        "Placement and research brief for the Governing Council for 2025-26",
        frozenset(),
        frozenset({"placement", "research"}), "2025-26", COUNCIL, "off_target",
    ),
    Case(
        "Finance brief for the Registrar for last year",
        frozenset(),
        frozenset({"finance"}), "2024-25", INTERNAL, "off_target",
    ),
    Case(
        "Brief for the board on everything, with options for every KPI, for 2024-25",
        frozenset(),
        ALL, "2024-25", COUNCIL, "all",
    ),
    Case(
        "Academic results for the Principal this year",
        frozenset(),
        frozenset({"academic"}), "current", INTERNAL, "off_target",
    ),
    Case(
        "Research output and grants brief for the council for 2023-24",
        frozenset(),
        frozenset({"research"}), "2023-24", COUNCIL, "off_target",
    ),
    Case(
        "Institution-wide overview for leadership for 2025-26, only the KPIs that are off target",
        frozenset(),
        ALL, "2025-26", INTERNAL, "off_target",
    ),
]  # fmt: skip

TODAY = date.today()


@dataclass
class PlannerRow:
    request: str
    ask_expected: list[str]
    ask_got: list[str] | None = None
    ask_exact: bool = False
    plan_fields: dict[str, bool] = field(default_factory=dict)
    plan_ok: bool | None = None
    calls: int = 0
    seconds: float = 0.0
    error: str | None = None


def build_model(args):
    settings = LlmSettings(
        provider=args.provider,
        base_url=args.base_url,
        model=args.model,
        allow_hosted=False,
        seed=args.seed,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    return get_chat_model("drafter", settings, SystemConfig("synthetic"))


def run_planner(model, catalogue: PlanCatalogue) -> list[PlannerRow]:
    rows = []
    for case in CASES:
        row = PlannerRow(case.request, sorted(case.ask))
        before = getattr(getattr(model, "stats", None), "calls", 0)
        started = time.monotonic()
        try:
            asked = clarify(model, case.request, [], catalogue)
            row.ask_got = sorted(q.id for q in asked)
            row.ask_exact = set(row.ask_got) == set(case.ask)
            if case.domains is not None:
                # the plan is judged on its own, as if the request had been enough: a model that asked
                # too much is scored for that above, not a second time here
                plan = propose_plan(model, case.request, [], catalogue)
                period = catalogue.current_period if case.period == "current" else case.period
                row.plan_fields = {
                    "period": plan.period_year == period,
                    "areas": {d.value for d in plan.domains} == set(case.domains),
                    "audience": plan.audience == case.audience,
                    "options_for": plan.options_for == case.options_for,
                }
                row.plan_ok = all(row.plan_fields.values())
        except (LLMOutputError, LLMUnavailable) as error:
            row.error = f"{type(error).__name__}: {str(error)[:160]}"
        row.seconds = time.monotonic() - started
        row.calls = getattr(getattr(model, "stats", None), "calls", before) - before
        rows.append(row)
        status = "ok" if (row.ask_exact and row.plan_ok in (True, None)) else "differs"
        print(
            f"  planner {len(rows):>2}/{len(CASES)} {status:7} {row.seconds:5.1f}s  {case.request[:60]}",
            flush=True,
        )
    return rows


@dataclass
class DraftRow:
    kpi: str
    seed: int
    drafted: bool = False
    first_try: bool = False  # no repair was needed inside the call
    calls: int = 0
    seconds: float = 0.0
    passed_gate: bool = False
    failing_checks: list[str] = field(default_factory=list)
    error: str | None = None


def run_drafter(args, store: DataStore, trials: int, used: list) -> list[DraftRow]:
    period = store.current_period
    previous = store.periods[store.periods.index(period) - 1]
    figures = []
    for d in store.definitions:
        result, before = store.result(d.key, period), store.result(d.key, previous)
        figures.append(
            figure_from(
                d, result, trend_word(result.value, before.value, result.target, d.higher_is_better)
            )
        )
    needing = off_target(figures)
    connector = InMemoryConnector(store, ScopeRegistry(TODAY))
    health = list(connector.get_data_health(period))
    plan = Plan(
        request="evaluation", period_year=period, domains=tuple(Domain(d) for d in ("academic", "research", "placement", "finance")),
        kpi_keys=tuple(f.key for f in figures), options_for="off_target", audience=INTERNAL, steps=(),
    )  # fmt: skip

    rows = []
    for figure in needing:
        for trial in range(trials):
            seed = args.seed + trial
            args_for_trial = argparse.Namespace(**{**vars(args), "seed": seed})
            model = build_model(args_for_trial)
            used.append(model)
            row = DraftRow(figure.key, seed)
            started = time.monotonic()
            try:
                option_set = draft_option_set(model, figure)
                row.drafted = True
                stats = getattr(model, "stats", None)
                row.calls = stats.calls if stats else 1
                row.first_try = row.calls == 1
                others = [f for f in needing if f.key != figure.key]
                from app.agents.llm import FakeLLM
                from app.agents.skills.options_skill import draft_option_set as canned_draft

                # the other KPIs' options come from the canned model, so one KPI's draft is judged alone
                sets = [option_set] + [canned_draft(FakeLLM("drafter"), f) for f in others]
                document = compose_brief(plan, figures, sets, health)
                report = validate(document, context_for_document(document, connector))
                row.passed_gate = report.passed
                row.failing_checks = [c.id for c in report.failing]
            except (LLMOutputError, LLMUnavailable) as error:
                row.error = f"{type(error).__name__}: {str(error)[:200]}"
                row.calls = getattr(getattr(model, "stats", None), "calls", 0)
            row.seconds = time.monotonic() - started
            rows.append(row)
            outcome = (
                "passes the gate"
                if row.passed_gate
                else (row.error or f"fails {row.failing_checks}")
            )
            print(
                f"  draft {figure.key:12} seed {seed:>3} {row.seconds:5.1f}s calls={row.calls} {outcome[:70]}",
                flush=True,
            )
    return rows


def pct(part: int, whole: int) -> str:
    return "n/a" if whole == 0 else f"{part}/{whole} ({100 * part / whole:.0f}%)"


def report(
    args, planner: list[PlannerRow], drafts: list[DraftRow], stats: Any, started: float
) -> str:
    asks = [r for r in planner if r.ask_got is not None]
    plans = [r for r in planner if r.plan_ok is not None]
    lines = [
        f"# Language model evaluation: {args.provider}:{args.model or 'canned'}",
        "",
        f"Run on {date.today().isoformat()}, synthetic data only, seed {args.seed}, temperature {args.temperature}, "
        f"{args.trials} draft trials per KPI. Total time {time.monotonic() - started:.0f} s.",
        "",
        "Labels are my reading of the requests, not ground truth from the university. "
        "The rule-based canned model is the baseline: run this script with `--provider fake` to see it.",
        "",
        "## Planner: ten requests",
        "",
        f"- Asked exactly the right questions: **{pct(sum(r.ask_exact for r in asks), len(planner))}**",
        f"- Plan fully right (period, areas, audience, options scope): **{pct(sum(bool(r.plan_ok) for r in plans), len(plans))}**",
    ]
    for name in ("period", "areas", "audience", "options_for"):
        lines.append(
            f"  - {name}: {pct(sum(r.plan_fields.get(name, False) for r in plans), len(plans))}"
        )
    failed = [r for r in planner if r.error]
    lines += [f"- Could not answer at all: **{len(failed)}**", ""]
    lines += ["| Request | Asked (expected) | Asked (got) | Plan |", "| --- | --- | --- | --- |"]
    for r in planner:
        plan = (
            "n/a"
            if r.plan_ok is None
            else (
                "right"
                if r.plan_ok
                else "wrong: " + ", ".join(k for k, v in r.plan_fields.items() if not v)
            )
        )
        lines.append(
            f"| {r.request} | {', '.join(r.ask_expected) or 'nothing'} | {', '.join(r.ask_got) if r.ask_got is not None else r.error} | {plan} |"
        )

    drafted = [d for d in drafts if d.drafted]
    lines += [
        "",
        "## Drafter: option text for every off-target KPI",
        "",
        f"Each draft is composed into a brief and put through checks V1 to V9. {len(drafts)} drafts.",
        "",
        f"- Produced a draft at all: **{pct(len(drafted), len(drafts))}**",
        f"- Needed no repair inside the call (first try): **{pct(sum(d.first_try for d in drafted), len(drafts))}**",
        f"- Passed the validation gate: **{pct(sum(d.passed_gate for d in drafts), len(drafts))}**",
    ]
    failing = Counter(c for d in drafts for c in d.failing_checks)
    if failing:
        lines.append(
            f"- Checks that failed: {', '.join(f'{c} x{n}' for c, n in sorted(failing.items()))}"
        )
    if drafts:
        seconds = [d.seconds for d in drafts]
        lines.append(
            f"- Time per draft: median {statistics.median(seconds):.1f} s, slowest {max(seconds):.1f} s"
        )
    if stats is not None and stats.calls:
        lines += [
            f"- Tokens: {stats.prompt_tokens} in, {stats.completion_tokens} out over {stats.calls} calls "
            f"({stats.completion_tokens / max(stats.seconds, 0.001):.0f} tokens per second)",
            f"- Empty answers (thinking used the budget): {stats.empty_answers}. Not JSON: {stats.not_json}",
        ]
    lines += ["", "| KPI | Seed | Calls | Seconds | Result |", "| --- | --- | --- | --- | --- |"]
    for d in drafts:
        result = "passes" if d.passed_gate else (d.error or f"fails {', '.join(d.failing_checks)}")
        lines.append(f"| {d.kpi} | {d.seed} | {d.calls} | {d.seconds:.1f} | {result} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--provider", default="ollama", choices=["fake", "ollama", "openai_compat"])
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=1500)
    parser.add_argument("--out", default="../docs/evals")
    parser.add_argument("--skip-planner", action="store_true")
    parser.add_argument("--skip-drafter", action="store_true")
    args = parser.parse_args()
    if args.provider == "fake":
        args.model = "canned"

    started = time.monotonic()
    store = DataStore.build(TODAY, 90)
    catalogue = PlanCatalogue(
        periods=store.periods,
        current_period=store.current_period,
        kpis=tuple(KpiInfo(d.key, d.name, d.domain) for d in store.definitions),
    )
    print(
        f"Evaluating {args.provider}:{args.model} (today is {TODAY}, current period {store.current_period})"
    )
    model = build_model(args)
    used = [model]  # every model built, so the cost line covers the planner and every draft
    try:
        planner = [] if args.skip_planner else run_planner(model, catalogue)
        drafts = [] if args.skip_drafter else run_drafter(args, store, args.trials, used)
    except LLMUnavailable as error:
        print(f"\nStopped: {error}", file=sys.stderr)
        return 2

    stats = None
    for m in used:
        s = getattr(m, "stats", None)
        if s is None:
            continue
        stats = stats or ModelStats()
        stats.calls += s.calls
        stats.prompt_tokens += s.prompt_tokens
        stats.completion_tokens += s.completion_tokens
        stats.seconds += s.seconds
        stats.not_json += s.not_json
        stats.empty_answers += s.empty_answers
    text = report(args, planner, drafts, stats, started)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    slug = f"{args.provider}-{args.model.replace(':', '-').replace('/', '-')}-{date.today().isoformat()}"
    (out / f"{slug}.md").write_text(text)
    (out / f"{slug}.json").write_text(
        json.dumps(
            {
                "provider": args.provider,
                "model": args.model,
                "seed": args.seed,
                "temperature": args.temperature,
                "trials": args.trials,
                "planner": [r.__dict__ for r in planner],
                "drafts": [d.__dict__ for d in drafts],
            },
            indent=2,
            default=str,
        )  # fmt: skip
    )
    print(f"\nWrote {out / (slug + '.md')}\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
