"""The options and risks skill (FR-5): draft two or three options for a KPI that is off target.

What the model is sent: the KPI's name, status, direction and trend as WORDS, and which
departments are flagged. Never a figure. What comes back: structured options whose numbers can
only be reference tokens, because check V1 rejects anything else. This is the one place a model
writes prose, and it is boxed in on both sides.

The FakeLLM handler at the bottom is the offline stand-in, a rule-based simulator. It can also
misbehave on purpose on its first attempt (`inject`), so failure injection has something real
to detect and repair.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, Field

from app.agents.fake_llm import register
from app.agents.llm import ChatModel
from app.agents.models import KpiFigure, Option, OptionSet
from app.agents.tokens import KPI_FIELDS, Ref, lint_numbers, parse_tokens
from app.domain.enums import KpiStatus

INJECTABLE_BY_MODEL = ("fake_number", "missing_risks", "provisional_as_final")


class OptionDraft(BaseModel):
    title: str
    description: str
    assumptions: list[str]
    risks: list[str]
    trade_offs: list[str]


class OptionSetDraft(BaseModel):
    options: list[OptionDraft] = Field(min_length=2, max_length=3)


def _direction(figure: KpiFigure) -> str:
    if figure.variance_abs is None:
        return "unknown"
    if figure.variance_abs < 0:
        return "below_target"
    return "above_target" if figure.variance_abs > 0 else "on_target"


def option_payload(
    figure: KpiFigure,
    *,
    attempt: int = 1,
    diagnosis: str | None = None,
    inject: Sequence[str] = (),
    fault_fact_id: int | None = None,
    framework: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Everything the model is told. No figures: statuses, directions and trends are words."""
    flags = figure.flags
    return {
        "kpi_key": figure.key,
        "kpi_name": figure.name,
        "domain": figure.domain.value,
        "status": figure.status.value,
        "direction": _direction(figure),
        "higher_is_better": figure.higher_is_better,
        "trend": figure.trend,
        "flags": {
            "stale": list(flags.stale_departments),
            "missing": list(flags.missing_departments),
            "excluded": list(flags.excluded_departments),
            "undefined": list(flags.undefined_departments),
        },
        "placeholder": figure.placeholder,
        # the specialist pack's guidance for this KPI's framework (Lab 13), in words
        "framework": dict(framework) if framework else None,
        "attempt": attempt,
        "diagnosis": diagnosis,
        "inject": list(inject),
        "fault_fact_id": fault_fact_id,
    }


def _check_options(figure: KpiFigure):
    """A quick pre-check for a real model, with feedback specific enough for it to fix itself.

    It is not the gate. Check V1 to V9 still decide, on everything, later. This only saves a
    small model the long way round: it is told "you wrote a number" now, instead of failing the
    gate and being told after the whole brief is composed.
    """

    def check(draft: OptionSetDraft) -> list[str]:
        problems: list[str] = []
        for number, option in enumerate(draft.options, start=1):
            texts = [
                option.title,
                option.description,
                *option.assumptions,
                *option.risks,
                *option.trade_offs,
            ]
            stray = sorted({fragment for text in texts for fragment in lint_numbers(text)})
            if stray:
                problems.append(
                    f"option {number} contains figures written by hand ({', '.join(stray[:5])}). "
                    "Write figures only as reference tokens, and avoid spelled-out numbers too"
                )
            for text in texts:
                for part in parse_tokens(text):
                    if isinstance(part, Ref) and (
                        part.kind != "kpi" or part.key != figure.key or part.field not in KPI_FIELDS
                    ):
                        problems.append(
                            f"option {number} uses a token that is not allowed ({part.kind}:{part.key}). "
                            f"Only {{{{kpi:{figure.key}}}}} with .target, .gap or .status may be used"
                        )
            for label, items in (
                ("assumptions", option.assumptions),
                ("risks", option.risks),
                ("trade_offs", option.trade_offs),
            ):
                if not [i for i in items if i.strip()]:
                    problems.append(f"option {number} needs at least one entry in {label}")
            if not option.title.strip() or not option.description.strip():
                problems.append(f"option {number} needs a title and a description")
        return list(dict.fromkeys(problems))

    return check


def _inject_into_draft(
    draft: OptionSetDraft, inject: Sequence[str], fault_fact_id: int | None
) -> OptionSetDraft:
    """Failure injection for a real model, done in code after it has answered.

    The FakeLLM misbehaves by itself when asked. A real model cannot be asked to, so the same
    faults are applied to what it returned. Either way the validation gate must catch them.
    """
    first = draft.options[0].model_copy()
    if "fake_number" in inject:
        first.description += " An increase of 12% is realistic within a year."
    if "missing_risks" in inject:
        first.risks = []
    if "provisional_as_final" in inject and fault_fact_id:
        first.description += (
            " {{fact:" + str(fault_fact_id) + "}} confirmed placements are already secured."
        )
    return OptionSetDraft(options=[first, *draft.options[1:]])


def draft_option_set(
    model: ChatModel,
    figure: KpiFigure,
    *,
    attempt: int = 1,
    diagnosis: str | None = None,
    inject: Sequence[str] = (),
    fault_fact_id: int | None = None,
    framework: Mapping[str, Any] | None = None,
) -> OptionSet:
    canned = getattr(model, "provider", "") == "fake"
    # a canned model misbehaves when asked, a real one has the faults applied to its answer
    payload = option_payload(
        figure,
        attempt=attempt,
        diagnosis=diagnosis,
        inject=inject if canned else (),
        fault_fact_id=fault_fact_id if canned else None,
        framework=framework,
    )
    draft = model.generate(  # type: ignore[attr-defined]
        "draft_options", payload, OptionSetDraft, check=_check_options(figure)
    )
    if not canned and attempt == 1 and inject:
        draft = _inject_into_draft(draft, inject, fault_fact_id)
    return OptionSet(
        kpi_key=figure.key,
        attempt=attempt,
        framework=figure.framework,
        options=tuple(
            Option(
                id=f"{figure.key}-{number}",
                title=item.title,
                description=item.description,
                assumptions=tuple(item.assumptions),
                risks=tuple(item.risks),
                trade_offs=tuple(item.trade_offs),
            )
            for number, item in enumerate(draft.options, start=1)
        ),
    )


# --- the FakeLLM stand-in --------------------------------------------------------------------
def _t(key: str, field: str = "") -> str:
    """A reference token for a KPI, written as text."""
    return "{{kpi:" + key + (f".{field}" if field else "") + "}}"


def _options_for(domain: str, key: str, trend: str) -> list[dict[str, Any]]:
    gap, value = _t(key, "gap"), _t(key)
    say = {"improving": "improving", "declining": "declining", "flat": "flat"}.get(trend, "unclear")
    library: dict[str, list[dict[str, Any]]] = {
        "academic": [
            {
                "title": "Targeted academic support in the departments below the line",
                "description": f"{value} is {gap}, and the trend is {say}. Concentrate remedial teaching, mentoring and examination preparation in the departments that pull the institution figure down, and review progress at every internal assessment.",
                "assumptions": [
                    "The department figures behind the institution figure describe current performance.",
                    "Remedial capacity exists in the weaker departments.",
                ],
                "risks": [
                    "Effort diverted from stronger departments may let their results slip.",
                    "Gains may take more than a semester to show.",
                ],
                "trade_offs": [
                    "Faster improvement in the weakest departments against a heavier load on a few faculty."
                ],
            },
            {
                "title": "Review assessment design and moderation",
                "description": f"A review of question paper design, moderation and evaluation practice would show whether {value} reflects learning or assessment difficulty, before any programme change is made.",
                "assumptions": [
                    "Assessment practice varies enough between departments to explain part of the gap."
                ],
                "risks": [
                    "Changing assessment may be read as lowering standards.",
                    "The review itself delays other remedies.",
                ],
                "trade_offs": ["A slower, more diagnostic route against quicker support measures."],
            },
            {
                "title": "Hold the current approach and monitor",
                "description": f"Keep current plans and watch {value} through the next assessment cycle, since it is {gap} and the trend is {say}.",
                "assumptions": ["No new factor is about to push the figure the wrong way."],
                "risks": [
                    "A narrow margin can disappear without warning.",
                    "Waiting may cost a cycle of improvement.",
                ],
                "trade_offs": ["No added effort now against a risk of acting late."],
            },
        ],
        "research": [
            {
                "title": "Seed grants and writing support for low-output departments",
                "description": f"{value} is {gap}, and the trend is {say}. Targeted seed grants, writing workshops and mentoring in departments with the lowest output would lift the institution figure fastest.",
                "assumptions": [
                    "Output is limited by support and time, not by the research agenda itself."
                ],
                "risks": [
                    "Support may raise the count of papers faster than their quality.",
                    "Benefits arrive after publication cycles, not immediately.",
                ],
                "trade_offs": [
                    "Concentrated funding in a few departments against broad, thinner support."
                ],
            },
            {
                "title": "Structured collaboration across departments",
                "description": f"Joint projects between departments could raise {value}, provided shared papers are counted once at institution level so the figure is not inflated.",
                "assumptions": [
                    "Departments have complementary strengths that are not yet being used together."
                ],
                "risks": [
                    "Collaboration adds coordination cost.",
                    "Credit disputes between departments may slow work.",
                ],
                "trade_offs": ["Richer joint output against slower individual progress."],
            },
            {
                "title": "Close the reporting gap before judging output",
                "description": f"Where a department has no record, {value} may understate real output. Complete the research register first, then judge the figure, since it is {gap}.",
                "assumptions": [
                    "Missing records reflect missing reporting rather than missing work."
                ],
                "risks": [
                    "Completing records may show the gap is real after all.",
                    "Time spent on records is time not spent on support.",
                ],
                "trade_offs": ["A more reliable figure against a delay in acting on it."],
            },
        ],
        "placement": [
            {
                "title": "Intensify pre-placement training where conversion is lowest",
                "description": f"{value} is {gap}, and the trend is {say}. Focus aptitude, communication and technical preparation on the departments where registered students are least often placed.",
                "assumptions": [
                    "Conversion differs by department for reasons training can address."
                ],
                "risks": [
                    "Training may not change recruiter demand for some branches.",
                    "Students may disengage if sessions clash with coursework.",
                ],
                "trade_offs": ["Depth in a few departments against even coverage everywhere."],
            },
            {
                "title": "Widen the recruiter pool and the sector mix",
                "description": f"Recruiter outreach beyond the usual companies, across more sectors, could raise {value} where local demand is thin.",
                "assumptions": [
                    "Recruiter interest, not student readiness, is the main limit in some departments."
                ],
                "risks": [
                    "New recruiters may offer lower packages.",
                    "Outreach takes a placement cycle to pay off.",
                ],
                "trade_offs": ["More offers against a possible fall in the average package."],
            },
            {
                "title": "Confirm provisional offers quickly",
                "description": f"Provisional offers are not counted in {value} until the Placement Cell verifies them. Verifying them promptly would show the true position, which is {gap} today.",
                "assumptions": ["Most provisional offers will be confirmed."],
                "risks": ["Some offers may be withdrawn, so the gain may be smaller than hoped."],
                "trade_offs": [
                    "Accuracy and speed of reporting against extra verification work for the cell."
                ],
            },
        ],
        "finance": [
            {
                "title": "Bring forward planned spending",
                "description": f"{value} is {gap}, and the trend is {say}. Release approved but unspent allocations earlier in the cycle, with department heads accountable for the plan.",
                "assumptions": ["Unspent allocations are held up by process, not by lack of need."],
                "risks": [
                    "Rushed spending may be poorly targeted.",
                    "Procurement rules limit how fast money can move.",
                ],
                "trade_offs": ["Higher utilisation against a risk of lower value for money."],
            },
            {
                "title": "Reconcile pending figures before the next review",
                "description": f"Some inputs to {value} are not yet reconciled, so it may be misleading. Complete reconciliation first, then act on the gap, which stands at {gap}.",
                "assumptions": ["Pending items are timing differences, not errors."],
                "risks": [
                    "Reconciliation may reveal a larger problem.",
                    "Decisions wait on the accounts office.",
                ],
                "trade_offs": ["A trustworthy figure against a delay in action."],
            },
            {
                "title": "Reallocate unspent budget across departments",
                "description": f"Move unspent allocations from slow departments to those that can use them within the year, to lift {value}.",
                "assumptions": [
                    "Some departments cannot spend their allocation in time while others could."
                ],
                "risks": [
                    "Departments may plan to spend less if they expect cuts.",
                    "Reallocation needs approval from the finance committee.",
                ],
                "trade_offs": [
                    "Better use of the whole budget against less predictability for each department."
                ],
            },
        ],
    }
    return library.get(domain, library["academic"])


def _flag_assumptions(flags: dict[str, list[str]]) -> list[str]:
    notes = []
    if flags.get("stale"):
        notes.append(
            f"{', '.join(flags['stale'])} data is stale, so its part in this picture may be out of date."
        )
    if flags.get("missing"):
        notes.append(
            f"{', '.join(flags['missing'])} has no record for the period and is not in the figure."
        )
    if flags.get("excluded"):
        notes.append(f"{', '.join(flags['excluded'])} is left out because an input is not final.")
    if flags.get("undefined"):
        notes.append(
            f"{', '.join(flags['undefined'])} has nothing to divide by, so it has no value here."
        )
    return notes


@register("draft_options")
def _fake_draft_options(payload: dict[str, Any]) -> dict[str, Any]:
    templates = _options_for(payload["domain"], payload["kpi_key"], payload["trend"])
    # three options for a miss, two for a KPI that is only at risk
    chosen = (
        templates if payload["status"] == KpiStatus.MISSED.value else [templates[0], templates[2]]
    )
    options = [dict(item) for item in chosen]
    options[0]["assumptions"] = [*options[0]["assumptions"], *_flag_assumptions(payload["flags"])]

    if payload["attempt"] == 1:  # a model misbehaving on its first try, only when asked to
        inject = payload.get("inject", [])
        if "fake_number" in inject:
            options[0]["description"] += " An increase of 12% is realistic within a year."
        if "missing_risks" in inject:
            options[0]["risks"] = []
        if "provisional_as_final" in inject and payload.get("fault_fact_id"):
            options[0]["description"] += (
                " {{fact:"
                + str(payload["fault_fact_id"])
                + "}} confirmed placements are already secured."
            )
    return {"options": options}
