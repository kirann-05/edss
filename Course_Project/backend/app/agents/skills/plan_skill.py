"""Clarify, plan, revise and lock (Lab 1, Lab 3, FR-1). One case-agnostic skill.

A vague request is not answered in one shot, that would be a chatbot. The skill asks what it
needs to know, proposes an editable outline, patches that same outline when a person gives
feedback, and locks it before any work begins. After the lock the plan cannot change, so the
run cannot drift from what was agreed.

What the model is sent is the request, the answers so far and a catalogue of what exists
(periods, areas, KPIs). It is never told a figure. Code decides the facts that matter: which
KPIs follow from which areas, and what changed between two versions of a plan.

With a real model the planner is a hybrid, rules first and the model second (decision D30). The
evaluation in docs/evals showed a small local model asking the right questions for 4 requests in
10, where a few dozen lines of word rules managed 9. So the rules decide wherever the request's
words say something. The model is asked only about what the rules cannot read, and where the two
disagree the person is asked. If the model's answer is unusable, planning carries on with the
rules; if the model server is down, that is said at once, because drafting will need it.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.agents.fake_llm import register
from app.agents.llm import ChatModel, LLMOutputError
from app.agents.models import Clarification, ClarifyQuestion, Plan, PlanStep
from app.domain.enums import Domain

AUDIENCES = ("Governing Council review", "Internal leadership review")
AREAS = (Domain.ACADEMIC, Domain.RESEARCH, Domain.PLACEMENT, Domain.FINANCE)
DOMAIN_LABEL = {
    Domain.ACADEMIC: "Academic",
    Domain.RESEARCH: "Research",
    Domain.PLACEMENT: "Placement",
    Domain.FINANCE: "Finance",
}


class PlanError(ValueError):
    """A plan that cannot be made, edited or locked."""


@dataclass(frozen=True)
class KpiInfo:
    key: str
    name: str
    domain: Domain


@dataclass(frozen=True)
class PlanCatalogue:
    """What a plan may choose from. Handed in, so the skill never reads data itself."""

    periods: tuple[str, ...]
    current_period: str
    kpis: tuple[KpiInfo, ...]

    def payload(self) -> dict[str, Any]:
        return {
            "periods": list(self.periods),
            "current_period": self.current_period,
            "kpis": [{"key": k.key, "name": k.name, "domain": k.domain.value} for k in self.kpis],
        }

    def by_key(self) -> dict[str, KpiInfo]:
        return {k.key: k for k in self.kpis}

    def keys_for(self, domains: Sequence[Domain]) -> tuple[str, ...]:
        return tuple(k.key for k in self.kpis if k.domain in domains)


# --- the shapes a model must return ----------------------------------------------------------
class QuestionDraft(BaseModel):
    id: str
    text: str
    why: str
    choices: list[str] = []


class ClarifyDraft(BaseModel):
    questions: list[QuestionDraft]


class StepDraft(BaseModel):
    id: str
    title: str
    detail: str


class PlanDraft(BaseModel):
    """The decisions in a plan. The outline's steps are written in code, never by a model: the
    pipeline is fixed, and a model must not be able to promise a step the graph does not run."""

    period_year: str
    domains: list[Domain]
    kpi_keys: list[str]
    options_for: Literal["off_target", "all"]
    audience: str
    steps: list[StepDraft] = []  # ignored. Kept so older canned outputs still fit


# --- the skill ----------------------------------------------------------------------------------
def _answers_payload(answers: Sequence[Clarification]) -> list[dict[str, str]]:
    return [{"question_id": a.question_id, "answer": a.answer} for a in answers]


Planner = Literal["hybrid", "model"]


def clarify(
    model: ChatModel,
    request: str,
    answers: Sequence[Clarification],
    catalogue: PlanCatalogue,
    planner: Planner = "hybrid",
) -> list[ClarifyQuestion]:
    """The questions still worth asking. An answered question is never asked again."""
    payload = {
        "request": request,
        "answers": _answers_payload(answers),
        "catalogue": catalogue.payload(),
    }
    if _canned(model) or planner == "model":
        draft = model.generate("clarify", payload, ClarifyDraft, check=_check_questions)  # type: ignore[attr-defined]
    else:
        draft = _hybrid_questions(model, payload)
    answered = {a.question_id for a in answers}
    questions: list[ClarifyQuestion] = []
    for q in draft.questions:
        # Only the three things a plan can use, each asked once. That bounds the conversation
        # whatever a model does: it cannot keep inventing new questions (rule 8, in spirit).
        if q.id not in ASKABLE or q.id in answered or any(q.id == done.id for done in questions):
            continue
        choices = tuple(reversed(catalogue.periods)) if q.id == "period" else tuple(q.choices)
        questions.append(ClarifyQuestion(id=q.id, text=q.text, why=q.why, choices=choices))
    return questions


ASKABLE = ("period", "scope", "audience")
DISAGREE = (
    " The language model read your request as already saying this, but none of its words do, "
    "so please choose."
)


def _canned(model: ChatModel) -> bool:
    return getattr(model, "provider", "") == "fake"


def _hybrid_questions(model: ChatModel, payload: dict[str, Any]) -> ClarifyDraft:
    """Ask what the rules cannot read in the words. The model is consulted only then, and a
    question the model thinks is already answered is still asked, saying so."""
    rules = ClarifyDraft.model_validate(_fake_clarify(payload))
    if not rules.questions:
        return rules  # the words say everything, so there is nothing to ask the model
    try:
        asked = {
            q.id
            for q in model.generate(
                "clarify", payload, ClarifyDraft, check=_check_questions
            ).questions
        }  # type: ignore[attr-defined]
    except LLMOutputError:
        return rules
    for question in rules.questions:
        if question.id not in asked:
            question.why += DISAGREE
    return rules


def _check_questions(draft: ClarifyDraft) -> list[str]:
    problems = []
    for q in draft.questions:
        if not q.text.strip() or not q.why.strip():
            problems.append(f"question {q.id!r} needs both a text and a why")
    return problems


def _check_plan(catalogue: PlanCatalogue) -> Callable[[PlanDraft], list[str]]:
    """What a schema cannot say: the period, the KPIs and the audience must really exist."""
    known = catalogue.by_key()

    def check(draft: PlanDraft) -> list[str]:
        problems = []
        if draft.period_year not in catalogue.periods:
            problems.append(
                f"period_year {draft.period_year!r} is not one of {list(catalogue.periods)}"
            )
        unknown = [k for k in draft.kpi_keys if k not in known]
        if unknown:
            problems.append(f"unknown kpi_keys {unknown}, copy keys exactly from the catalogue")
        if not draft.kpi_keys and not draft.domains:
            problems.append("choose at least one area or one KPI")
        if draft.audience not in AUDIENCES:
            problems.append(f"audience must be exactly one of {list(AUDIENCES)}")
        return problems

    return check


def _to_plan(draft: PlanDraft, request: str, revision: int, catalogue: PlanCatalogue) -> Plan:
    """The model decides what the plan is about. Code decides everything that follows from it."""
    known = catalogue.by_key()
    chosen = set(draft.kpi_keys) or set(catalogue.keys_for(draft.domains))
    keys = tuple(k.key for k in catalogue.kpis if k.key in chosen)  # catalogue order, no repeats
    domains = tuple(d for d in AREAS if any(known[k].domain is d for k in keys))
    steps = _steps(
        draft.period_year, [d.value for d in domains], len(keys), draft.options_for, draft.audience
    )
    return Plan(
        request=request,
        period_year=draft.period_year,
        domains=domains,
        kpi_keys=keys,
        options_for=draft.options_for,
        audience=draft.audience,
        steps=tuple(PlanStep(id=s["id"], title=s["title"], detail=s["detail"]) for s in steps),
        revision=revision,
    )


def propose_plan(
    model: ChatModel,
    request: str,
    answers: Sequence[Clarification],
    catalogue: PlanCatalogue,
    planner: Planner = "hybrid",
) -> Plan:
    payload = {
        "request": request,
        "answers": _answers_payload(answers),
        "catalogue": catalogue.payload(),
    }
    if _canned(model) or planner == "model":
        draft = model.generate("propose_plan", payload, PlanDraft, check=_check_plan(catalogue))  # type: ignore[attr-defined]
    else:
        draft = _hybrid_plan(model, payload, catalogue)
    return _to_plan(draft, request, revision=1, catalogue=catalogue)


def _hybrid_plan(model: ChatModel, payload: dict[str, Any], catalogue: PlanCatalogue) -> PlanDraft:
    """The rules' plan, with the model's reading only for what the words did not say, which can
    happen only when the person skipped the questions. Whether to draft options for every KPI is
    never left to the model: it is a request a person makes in words, or it is off target."""
    rules = PlanDraft.model_validate(_fake_propose_plan(payload))
    text, raw = _all_text(payload), payload["catalogue"]
    unread = {
        "period_year": _period_in(text, raw["periods"], raw["current_period"]) is None,
        "domains": not _mentioned_areas(text),
        "audience": _audience_in(text) is None,
    }
    if not any(unread.values()):
        return rules
    try:
        read = model.generate("propose_plan", payload, PlanDraft, check=_check_plan(catalogue))  # type: ignore[attr-defined]
    except LLMOutputError:
        return rules
    chosen = {field: getattr(read, field) for field, missing in unread.items() if missing}
    if "domains" in chosen and not chosen["domains"]:
        del chosen["domains"]
    if "domains" in chosen:
        chosen["kpi_keys"] = []  # the areas decide the KPIs, in code
    return rules.model_copy(update=chosen)


def revise_plan(
    model: ChatModel, plan: Plan, feedback: str, catalogue: PlanCatalogue
) -> tuple[Plan, list[str]]:
    """Patch the plan from feedback. Returns the new plan and, worked out in code, what changed."""
    if plan.locked:
        raise PlanError("the plan is locked, so it can no longer be revised")
    draft = model.generate(  # type: ignore[attr-defined]
        "revise_plan",
        {
            "plan": plan.model_dump(mode="json"),
            "feedback": feedback,
            "catalogue": catalogue.payload(),
        },
        PlanDraft,
        check=_check_plan(catalogue),
    )
    revised = _to_plan(draft, plan.request, revision=plan.revision + 1, catalogue=catalogue)
    return revised, diff_plans(plan, revised, catalogue)


def lock_plan(plan: Plan, at: datetime) -> Plan:
    if plan.locked:
        raise PlanError("the plan is already locked")
    if not plan.kpi_keys or not plan.domains:
        raise PlanError("a plan needs at least one area and one KPI before it can be locked")
    return plan.model_copy(update={"locked_at": at})


def apply_patch(plan: Plan, patch: dict[str, Any], catalogue: PlanCatalogue) -> Plan:
    """A person edits the outline directly. Everything is checked against the catalogue."""
    if plan.locked:
        raise PlanError("the plan is locked, so it can no longer be edited")
    known = catalogue.by_key()
    updates: dict[str, Any] = {}

    if "period_year" in patch:
        if patch["period_year"] not in catalogue.periods:
            raise PlanError(f"{patch['period_year']!r} is not a period we have data for")
        updates["period_year"] = patch["period_year"]
    if "options_for" in patch:
        if patch["options_for"] not in ("off_target", "all"):
            raise PlanError("options_for must be off_target or all")
        updates["options_for"] = patch["options_for"]
    if "audience" in patch:
        if not str(patch["audience"]).strip():
            raise PlanError("the audience cannot be blank")
        updates["audience"] = str(patch["audience"]).strip()

    domains = plan.domains
    if "domains" in patch:
        try:
            domains = tuple(Domain(d) for d in patch["domains"])
        except ValueError as error:
            raise PlanError(f"unknown area: {error}") from None
        if not domains or any(d not in AREAS for d in domains):
            raise PlanError("a plan needs at least one of the four areas")
        updates["domains"] = domains
        if "kpi_keys" not in patch:
            updates["kpi_keys"] = catalogue.keys_for(domains)
    if "kpi_keys" in patch:
        keys = tuple(patch["kpi_keys"])
        if not keys:
            raise PlanError("a plan needs at least one KPI")
        missing = [k for k in keys if k not in known]
        if missing:
            raise PlanError(f"unknown KPI {missing[0]!r}")
        updates["kpi_keys"] = keys
        if "domains" not in patch:
            wanted = {known[k].domain for k in keys}
            updates["domains"] = tuple(d for d in AREAS if d in wanted)

    if "steps" in patch:
        by_id = {s.id: s for s in plan.steps}
        edited = dict(by_id)
        for step_id, change in patch["steps"].items():
            if step_id not in by_id:
                raise PlanError(f"there is no step {step_id!r}")
            edited[step_id] = by_id[step_id].model_copy(
                update={k: v for k, v in change.items() if k in ("title", "detail")}
            )
        updates["steps"] = tuple(edited[s.id] for s in plan.steps)

    return plan.model_copy(update={**updates, "revision": plan.revision + 1})


def diff_plans(old: Plan, new: Plan, catalogue: PlanCatalogue) -> list[str]:
    """What changed, in plain words, decided in code."""
    known = catalogue.by_key()
    changes: list[str] = []
    if new.period_year != old.period_year:
        changes.append(f"Period set to {new.period_year}")

    added = [d for d in new.domains if d not in old.domains]
    dropped = [d for d in old.domains if d not in new.domains]
    for domain in added:
        changes.append(f"Added {DOMAIN_LABEL[domain]}")
    for domain in dropped:
        count = sum(1 for k in old.kpi_keys if k in known and known[k].domain is domain)
        changes.append(f"Dropped {DOMAIN_LABEL[domain]} ({count} KPI{'s' if count != 1 else ''})")

    moved = set(added) | set(dropped)
    for key in sorted(set(new.kpi_keys) - set(old.kpi_keys)):
        if key in known and known[key].domain not in moved:
            changes.append(f"Added KPI {known[key].name}")
    for key in sorted(set(old.kpi_keys) - set(new.kpi_keys)):
        if key in known and known[key].domain not in moved:
            changes.append(f"Dropped KPI {known[key].name}")

    if new.options_for != old.options_for:
        changes.append(
            "Options will be drafted for every KPI"
            if new.options_for == "all"
            else "Options will be drafted only for KPIs that are off target"
        )
    if new.audience != old.audience:
        changes.append(f"Audience set to {new.audience}")
    return changes


# --- the FakeLLM stand-ins ----------------------------------------------------------------------
_PERIOD = re.compile(r"\b(20\d{2}-\d{2})\b")
_ALL_AREAS = ("all four", "all areas", "all domains", "every area", "everything", "institution-wide",
              "institution wide", "whole institution", "overall")  # fmt: skip
_AREA_WORDS = {
    Domain.ACADEMIC: ("academic", "pass rate", "pass percentage", "attainment", "curriculum", "exam"),
    Domain.RESEARCH: ("research", "publication", "citation", "papers"),
    Domain.PLACEMENT: ("placement", "placed", "package", "internship", "recruit"),
    Domain.FINANCE: ("finance", "financial", "budget", "revenue", "expenditure", "utilisation", "utilization"),
}  # fmt: skip
_EVERY_KPI = ("every kpi", "all kpis", "all the kpis", "each kpi")
_OFF_TARGET = ("off target", "off-target", "missed", "shortfall")


def _mentioned_areas(text: str) -> list[Domain]:
    lowered = text.lower()
    if any(w in lowered for w in _ALL_AREAS):
        return list(AREAS)
    return [d for d in AREAS if any(w in lowered for w in _AREA_WORDS[d])]


def _audience_in(text: str) -> str | None:
    lowered = text.lower()
    if any(w in lowered for w in ("council", "board", "governing")):
        return AUDIENCES[0]
    if any(w in lowered for w in ("internal", "principal", "registrar", "review meeting")):
        return AUDIENCES[1]
    return None


def _period_in(text: str, periods: list[str], current: str) -> str | None:
    for match in _PERIOD.finditer(text):
        if match.group(1) in periods:
            return match.group(1)
    lowered = text.lower()
    if any(w in lowered for w in ("this year", "current year", "latest")):
        return current
    if any(w in lowered for w in ("last year", "previous year")) and current in periods:
        index = periods.index(current)
        return periods[index - 1] if index > 0 else None
    return None


def _all_text(payload: dict[str, Any]) -> str:
    return " ".join([payload["request"], *(a["answer"] for a in payload.get("answers", []))])


@register("clarify")
def _fake_clarify(payload: dict[str, Any]) -> dict[str, Any]:
    catalogue = payload["catalogue"]
    text = _all_text(payload)
    answered = {a["question_id"] for a in payload.get("answers", [])}
    questions = []
    if (
        "period" not in answered
        and _period_in(text, catalogue["periods"], catalogue["current_period"]) is None
    ):
        questions.append({
            "id": "period",
            "text": "Which period should the brief cover?",
            "why": "Figures are decided per academic year, and targets differ from year to year.",
            "choices": list(reversed(catalogue["periods"])),
        })  # fmt: skip
    if "scope" not in answered and not _mentioned_areas(text):
        questions.append({
            "id": "scope",
            "text": "Which areas should it cover?",
            "why": "Each area has its own agent and data owner, and access is authorised area by area.",
            "choices": ["All four areas", *(DOMAIN_LABEL[d] for d in AREAS)],
        })  # fmt: skip
    if "audience" not in answered and _audience_in(text) is None:
        questions.append({
            "id": "audience",
            "text": "Who will read it?",
            "why": "The reader decides how much caution and detail the brief needs.",
            "choices": list(AUDIENCES),
        })  # fmt: skip
    return {"questions": questions}


def _steps(
    period: str, domains: list[str], count: int, options_for: str, audience: str
) -> list[dict[str, str]]:
    names = ", ".join(DOMAIN_LABEL[Domain(d)] for d in domains)
    scope = "every KPI" if options_for == "all" else "every KPI that is off target"
    return [
        {"id": "access", "title": "Confirm access",
         "detail": f"Check that the Registrar has authorised read access to {names}."},
        {"id": "aggregate", "title": "Aggregate each area in parallel",
         "detail": f"{names} each read their department data at the same time, through the connector."},
        {"id": "synthesise", "title": "Compute the KPIs",
         "detail": f"Compute {count} KPIs for {period} from the active definitions, with target and variance, from unrounded values."},
        {"id": "options", "title": "Draft options and risks",
         "detail": f"Draft two or three options, with assumptions, risks and trade-offs, for {scope}."},
        {"id": "validate", "title": "Validate",
         "detail": "Run the nine checks. If one fails, regenerate only the failing part, up to the retry budget, then hand it to a person."},
        {"id": "review", "title": "Human review",
         "detail": f"A named approver reviews the brief for the {audience} and approves, edits or overrides it."},
    ]  # fmt: skip


def _draft(
    period: str, domains: list[str], keys: list[str], options_for: str, audience: str
) -> dict[str, Any]:
    return {
        "period_year": period,
        "domains": domains,
        "kpi_keys": keys,
        "options_for": options_for,
        "audience": audience,
        "steps": _steps(period, domains, len(keys), options_for, audience),
    }


def _keys_for(catalogue: dict[str, Any], domains: list[str]) -> list[str]:
    return [k["key"] for k in catalogue["kpis"] if k["domain"] in domains]


@register("propose_plan")
def _fake_propose_plan(payload: dict[str, Any]) -> dict[str, Any]:
    catalogue = payload["catalogue"]
    text = _all_text(payload)
    period = (
        _period_in(text, catalogue["periods"], catalogue["current_period"])
        or catalogue["current_period"]
    )
    domains = [d.value for d in (_mentioned_areas(text) or list(AREAS))]
    audience = _audience_in(text) or AUDIENCES[1]
    options_for = "all" if any(w in text.lower() for w in _EVERY_KPI) else "off_target"
    return _draft(period, domains, _keys_for(catalogue, domains), options_for, audience)


_DROP = re.compile(r"(?:drop|remove|exclude|without|skip|leave out)\b[^.;]{0,30}$", re.IGNORECASE)
_ADD = re.compile(r"(?:add|include|also|with)\b[^.;]{0,30}$", re.IGNORECASE)


def _domain_edits(feedback: str, current: list[str]) -> list[str]:
    lowered = feedback.lower()
    mentioned = _mentioned_areas(feedback)
    if re.search(r"\bonly\b", lowered) and mentioned:
        return [d.value for d in mentioned]
    result = list(current)
    for domain in AREAS:
        for word in _AREA_WORDS[domain]:
            for match in re.finditer(re.escape(word), lowered):
                before = lowered[: match.start()]
                if _DROP.search(before) and domain.value in result:
                    result.remove(domain.value)
                elif _ADD.search(before) and domain.value not in result:
                    result.append(domain.value)
    return [d.value for d in AREAS if d.value in result]


@register("revise_plan")
def _fake_revise_plan(payload: dict[str, Any]) -> dict[str, Any]:
    plan, feedback, catalogue = payload["plan"], payload["feedback"], payload["catalogue"]
    domains = _domain_edits(feedback, plan["domains"])
    keys = [k for k in plan["kpi_keys"] if any(
        info["key"] == k and info["domain"] in domains for info in catalogue["kpis"]
    )]  # fmt: skip
    for added in [d for d in domains if d not in plan["domains"]]:
        keys += [k for k in _keys_for(catalogue, [added]) if k not in keys]

    known = {k["key"] for k in catalogue["kpis"]}
    for match in re.finditer(r"\b[A-Z]{2}_[A-Z_]+\b", feedback):
        key = match.group()
        if key not in known:
            continue
        before = feedback[: match.start()]
        if _DROP.search(before) and key in keys:
            keys.remove(key)
        elif _ADD.search(before) and key not in keys:
            keys.append(key)
    order = {k["key"]: i for i, k in enumerate(catalogue["kpis"])}
    keys.sort(key=lambda k: order[k])

    period = (
        _period_in(feedback, catalogue["periods"], catalogue["current_period"])
        or plan["period_year"]
    )
    lowered = feedback.lower()
    options_for = plan["options_for"]
    if any(w in lowered for w in _EVERY_KPI):
        options_for = "all"
    elif any(w in lowered for w in _OFF_TARGET):
        options_for = "off_target"
    audience = _audience_in(feedback) or plan["audience"]
    return _draft(period, domains, keys, options_for, audience)
