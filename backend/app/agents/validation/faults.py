"""Failure injection (docs/ARCHITECTURE.md section 10, Lab 10).

Each function takes a clean brief and breaks it in one specific, realistic way. The tests assert
that the matching check catches it, and the demo can switch the same faults on live. Faults that
come from a model misbehaving (a fake number, missing risks, a provisional figure called
confirmed) are also available through the FakeLLM, see skills/options_skill.py.
"""

from collections.abc import Callable

from app.agents.figures import hides_miss
from app.agents.models import BriefDocument, KpiFigure, OptionSet
from app.agents.validation.checks import UNIQUE_PUBLICATIONS, ValidationContext
from app.domain.enums import FactStatus, KpiStatus
from app.kpi.formulas import InputTerm


def _edit_first_option(doc: BriefDocument, **changes) -> BriefDocument:
    first = doc.option_sets[0]
    edited = first.options[0].model_copy(update=changes)
    replaced = OptionSet(
        kpi_key=first.kpi_key, attempt=first.attempt, options=(edited, *first.options[1:])
    )
    return doc.model_copy(update={"option_sets": (replaced, *doc.option_sets[1:])})


def _edit_figure(doc: BriefDocument, key: str, **changes) -> BriefDocument:
    figures = tuple(f.model_copy(update=changes) if f.key == key else f for f in doc.kpis)
    return doc.model_copy(update={"kpis": figures})


def fake_number(doc: BriefDocument, ctx: ValidationContext) -> BriefDocument:
    first = doc.option_sets[0].options[0]
    return _edit_first_option(doc, description=first.description + " Raise it by 12%.")


def dropped_source(doc: BriefDocument, ctx: ValidationContext) -> BriefDocument:
    figure = next(f for f in doc.kpis if f.value is not None and f.input_fact_ids)
    return _edit_figure(doc, figure.key, input_fact_ids=())


def provisional_as_final(doc: BriefDocument, ctx: ValidationContext) -> BriefDocument:
    fact = next(f for f in ctx.facts.values() if f.status is FactStatus.PROVISIONAL)
    first = doc.option_sets[0].options[0]
    text = f"{first.description} {{{{fact:{fact.id}}}}} confirmed placements are already secured."
    return _edit_first_option(doc, description=text)


def missing_risks(doc: BriefDocument, ctx: ValidationContext) -> BriefDocument:
    return _edit_first_option(doc, risks=())


def stale_hidden(doc: BriefDocument, ctx: ValidationContext) -> BriefDocument:
    return doc.model_copy(
        update={
            "assumptions": tuple(a for a in doc.assumptions if a.kind != "stale"),
            "data_health": tuple(n for n in doc.data_health if n.state != "stale"),
        }
    )


def double_count(doc: BriefDocument, ctx: ValidationContext) -> BriefDocument:
    figure = next(f for f in doc.kpis if any(t.label == UNIQUE_PUBLICATIONS for t in f.inputs))
    inputs = tuple(
        InputTerm(label=t.label, value=t.value + 5) if t.label == UNIQUE_PUBLICATIONS else t
        for t in figure.inputs
    )
    return _edit_figure(doc, figure.key, inputs=inputs)


def rounded_miss(doc: BriefDocument, ctx: ValidationContext) -> BriefDocument:
    """A miss that rounds to its target, marked as met, as if status were decided after rounding."""
    missed = [f for f in doc.kpis if f.status is KpiStatus.MISSED]
    hidden = [f for f in missed if hides_miss(f.value, f.target, f.precision, f.status)]
    figure: KpiFigure = (hidden or missed)[0]
    return _edit_figure(doc, figure.key, status=KpiStatus.MET)


def approval_bypass(doc: BriefDocument, ctx: ValidationContext) -> BriefDocument:
    return doc.model_copy(update={"claims_status": "approved"})


_FAULTS: dict[str, Callable[[BriefDocument, ValidationContext], BriefDocument]] = {
    "fake_number": fake_number,
    "dropped_source": dropped_source,
    "provisional_as_final": provisional_as_final,
    "missing_risks": missing_risks,
    "stale_hidden": stale_hidden,
    "double_count": double_count,
    "rounded_miss": rounded_miss,
    "approval_bypass": approval_bypass,
}

FAULTS: tuple[str, ...] = tuple(_FAULTS)


def apply_fault(doc: BriefDocument, fault: str, ctx: ValidationContext) -> BriefDocument:
    try:
        return _FAULTS[fault](doc, ctx)
    except KeyError:
        raise ValueError(f"unknown fault {fault!r}, expected one of {FAULTS}") from None
