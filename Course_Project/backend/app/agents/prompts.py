"""What a real model is told, task by task (docs/ARCHITECTURE.md section 5).

The FakeLLM needs none of this, it is code. A real model needs instructions, and the instructions
carry the project's rules, because a rule the model has not been told is a rule it will break:

  * it is never given a figure, so it cannot repeat one wrongly, and
  * it is told that figures reach the text only as reference tokens, in code, after it has written.

The prompts are plain data in this file so they can be read, reviewed and changed without
touching any logic, and so an evaluation run records exactly which wording produced which result.
Worked examples are built from the real periods, never hard-coded, so they cannot disagree with
the data. They deliberately use requests unlike the ones in scripts/evaluate_llm.py, so measuring
a model is not marking it on its own examples.
"""

import json
from typing import Any

COUNCIL = "Governing Council review"
INTERNAL = "Internal leadership review"

# every task shares this, so a rule is stated once
_RULES = """You are one step inside a decision support system used by a university's leadership \
(the Principal, the Registrar, deans). People review and approve everything you write before it \
is used. Answer only with JSON that fits the schema you are given.

Rules you must follow:
- Never write a number. No digits, and no spelled-out numbers (two, three, twelve, hundred, half, \
double, and so on). Say "several", "a few", "most" or "the weakest departments" instead. Years in \
the form 2025-26 are fine.
- You are never told any figure and must not guess one.
- Write plainly, for a busy reader. No hype, no jargon, no emoji."""

# how a request's words map onto the system's vocabulary, shared by the planning tasks
_VOCABULARY = """How to read a request:
- Period: "this year", "current" or "latest" mean current_period. "last year" or "previous year" \
mean the period just before current_period in the list. A period written like 2024-25 means that \
period. If the request says nothing about the period, it is not named.
- Areas: academic (results, pass rate, curriculum, attainment, exams), research (publications, \
citations, grants, papers), placement (placements, packages, internships, recruiters), finance \
(budget, spending, utilisation, revenue, expenditure). "Everything", "all areas", "overall" or \
"institution-wide" mean all four. If no area is named, none is known.
- Audience: council, board or governing body means "Governing Council review". Principal, \
Registrar, Dean, leadership or internal means "Internal leadership review". If none is named, it \
is not known."""

_CLARIFY = """TASK: decide what you still need to ask before a plan can be made.

{vocabulary}

You are given the person's request, the answers they have already given, and the catalogue of \
what exists (academic periods, KPIs and their areas).

Ask only about what is genuinely missing. A thing is already known when the request or an earlier \
answer names it, so never ask about it. Check each of the three things below against the request \
and the answers before asking. The three things that can be missing are:
- id "period": which academic period. Choices must be copied from the catalogue's periods, newest first.
- id "scope": which areas to cover. Choices: "All four areas", "Academic", "Research", "Placement", "Finance".
- id "audience": who will read it. Choices: "Governing Council review", "Internal leadership review".

Never ask a question whose id already has an answer. If nothing is missing, return an empty list, \
which is the right answer for a request that names a period, an area and an audience. Each \
question needs a short plain "text" and a one-sentence "why" that tells the person why you need \
it. Ask at most three questions."""

_PLAN = """TASK: turn the request into a plan: the decisions only. The steps are written elsewhere.

{vocabulary}

You are given the request, the answers so far, and the catalogue (periods, KPIs with their areas). \
Decide:
- period_year: copy exactly one of the catalogue's periods, reading the request as described above.
- domains: only the areas the request names, from: academic, research, placement, finance. Use all \
four only when the request says everything, all areas, overall or institution-wide, or names none.
- kpi_keys: leave this as an empty list unless the request names particular KPIs, then copy their \
keys exactly from the catalogue. The KPIs of the chosen areas are filled in for you.
- options_for: "all" only if the person asks for options on every KPI, otherwise "off_target".
- audience: exactly "Governing Council review" or "Internal leadership review", as described above. \
If none is named, use "Internal leadership review".
Return an empty list for steps."""

_REVISE = """TASK: change an existing plan according to the person's feedback.

{vocabulary}

You are given the current plan, the feedback and the catalogue. Return the full plan again with \
only the changes the feedback asks for, using the same rules as when a plan is first made: \
period_year must be copied exactly from the catalogue, kpi_keys is empty unless particular KPIs \
are named, and options_for is "all" or "off_target". If the feedback asks to drop an area, remove \
it from domains. If it asks for something that does not exist, leave the plan unchanged. \
Return an empty list for steps."""

_OPTIONS = """TASK: draft options for one KPI that is off target, for the leadership to decide on.

You are given the KPI's name, its area, whether it is missed or at risk, which way it differs \
from target (words only), its trend, and data-quality flags for departments. You are not given \
any figure, on purpose. You may also be given "framework": the planning framework this KPI \
belongs to, with guidance and the areas every option should weigh. Follow that guidance, and let \
the areas shape the assumptions, risks and trade-offs.

Write two or three genuinely different options. Each option has:
- title: a short plain title.
- description: what would be done and why it could help, in two or three sentences.
- assumptions: what must be true for it to work. At least one.
- risks: what could go wrong. At least one.
- trade_offs: what is given up for what is gained. At least one.

REFERENCE TOKENS. To mention the KPI's figure you must use these tokens exactly, they are filled \
in with the real figure after you write:
- {{kpi:KEY}} the KPI's value
- {{kpi:KEY.target}} its target
- {{kpi:KEY.gap}} the gap to target, already in words such as "below target"
- {{kpi:KEY.status}} its status in words
where KEY is the kpi_key you were given. Use no other token. Never write {{fact:...}}.

Other rules for this task:
- The first option's description should mention the value with {{kpi:KEY}} and the gap with {{kpi:KEY.gap}}.
- If departments are listed as stale, missing, excluded or undefined, say in an assumption that \
the picture may be incomplete there. Never treat a missing department as zero.
- Options are drafts for people to decide on. Do not say anything has been done or approved, and \
do not describe a provisional or forecast figure as final.
- Do not invent causes as facts. Say "may" or "could" when something is uncertain.
- Write time and amounts without number words: "a year", "a semester", "the next cycle", "a few \
departments", "several", "most", "much faster". Never "one year", "two quarters", "twice", "half".

If you are given "validation_error" and "previous_output", your last answer was rejected. If you \
are given "diagnosis", the last draft failed a check for that reason. Fix exactly what is said \
and keep everything else that was fine."""

SYSTEM: dict[str, str] = {
    "clarify": _CLARIFY,
    "propose_plan": _PLAN,
    "revise_plan": _REVISE,
    "draft_options": _OPTIONS,
}

_PLAN_TASKS = ("clarify", "propose_plan")
HIDDEN = {"inject", "fault_fact_id", "repair_round"}  # for the machinery, never for the model


class UnknownTask(KeyError):
    """A task a real model has no prompt for."""


def _example_catalogue(payload: dict[str, Any]) -> dict[str, Any] | None:
    catalogue = payload.get("catalogue") or {}
    periods, current = catalogue.get("periods") or [], catalogue.get("current_period")
    if not periods or current not in periods:
        return None
    return {"periods": periods, "current_period": current}


def examples(task: str, payload: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Worked examples for a task, built from the real periods so they are always consistent.

    Examples carry no KPI list, because the planning decisions do not need one.
    """
    catalogue = _example_catalogue(payload)
    if catalogue is None or task not in _PLAN_TASKS:
        return []
    periods, current = catalogue["periods"], catalogue["current_period"]
    previous = periods[max(periods.index(current) - 1, 0)]
    oldest = periods[0]

    def sample(request: str) -> dict[str, Any]:
        return {"request": request, "answers": [], "catalogue": catalogue}

    if task == "clarify":
        period_q = {
            "id": "period",
            "text": "Which period should the brief cover?",
            "why": "Figures are decided per academic year, and targets differ from year to year.",
            "choices": list(reversed(periods)),
        }
        scope_q = {
            "id": "scope",
            "text": "Which areas should it cover?",
            "why": "Each area has its own agent and data owner.",
            "choices": ["All four areas", "Academic", "Research", "Placement", "Finance"],
        }
        audience_q = {
            "id": "audience",
            "text": "Who will read it?",
            "why": "The reader decides how much caution and detail the brief needs.",
            "choices": [COUNCIL, INTERNAL],
        }
        return [
            (sample("Prepare the brief"), {"questions": [period_q, scope_q, audience_q]}),
            (sample(f"Budget and spending brief for the Registrar, {previous}"), {"questions": []}),
            (sample("Research update"), {"questions": [period_q, audience_q]}),
            (sample("Brief for the board on everything this year"), {"questions": []}),
        ]

    def plan(period: str, domains: list[str], options_for: str, audience: str) -> dict[str, Any]:
        return {
            "period_year": period,
            "domains": domains,
            "kpi_keys": [],
            "options_for": options_for,
            "audience": audience,
            "steps": [],
        }

    all_four = ["academic", "research", "placement", "finance"]
    return [
        (
            sample("Research brief for the Dean for last year"),
            plan(previous, ["research"], "off_target", INTERNAL),
        ),
        (
            sample(f"Everything for the Governing Council, options on every KPI, {oldest}"),
            plan(oldest, all_four, "all", COUNCIL),
        ),
        (
            sample("Academic and finance for the Registrar this year"),
            plan(current, ["academic", "finance"], "off_target", INTERNAL),
        ),
        (
            sample("Placement update for the board"),
            plan(current, ["placement"], "off_target", COUNCIL),
        ),
    ]


def build_messages(task: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    """System prompt, worked examples, then the real input. The payload is always sent as JSON."""
    try:
        instructions = SYSTEM[task]
    except KeyError:
        raise UnknownTask(f"there is no prompt for the task {task!r}") from None
    messages = [
        {
            "role": "system",
            "content": f"{_RULES}\n\n{instructions.replace('{vocabulary}', _VOCABULARY)}",
        }
    ]
    for sample_input, sample_answer in examples(task, payload):
        messages.append({"role": "user", "content": json.dumps(sample_input, ensure_ascii=False)})
        messages.append(
            {"role": "assistant", "content": json.dumps(sample_answer, ensure_ascii=False)}
        )
    visible = {k: v for k, v in payload.items() if k not in HIDDEN}
    messages.append(
        {"role": "user", "content": json.dumps(visible, indent=2, ensure_ascii=False, default=str)}
    )
    return messages
