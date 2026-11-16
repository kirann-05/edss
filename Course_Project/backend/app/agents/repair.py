"""Diagnose, then regenerate only the part that failed (Lab 10, rule 8).

The validation report says where each failure is and how to put it right. This module does
exactly that and nothing more: an option set is drafted again with the diagnosis, a corrupted
figure is rebuilt from the KPI engine (never patched), a section is derived again, a false claim
of approval is reset. Everything that was fine is left as it was.

The loop is bounded. After `max_attempts` looks it stops and hands over, still failing, with the
diagnosis, so a person decides. It never spins.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.agents.compose import build_assumptions, build_health_notes, build_summary
from app.agents.connector import HealthCellInfo
from app.agents.frameworks import FrameworkGuide
from app.agents.llm import ChatModel
from app.agents.models import BriefDocument, KpiFigure, OptionSet, Plan, ValidationReport
from app.agents.skills.options_skill import draft_option_set
from app.agents.validation.checks import ValidationContext
from app.agents.validation.suite import validate
from app.domain.enums import Domain


@dataclass(frozen=True)
class RepairContext:
    plan: Plan
    figures: Mapping[str, KpiFigure]  # straight from the engine, the one source of truth
    health: Sequence[HealthCellInfo]
    model: ChatModel
    frameworks: FrameworkGuide | None = None  # the specialist packs, so a repair is guided too


def _in_plan_order(plan: Plan, items, key):
    order = {k: i for i, k in enumerate(plan.kpi_keys)}
    return tuple(sorted(items, key=lambda item: order.get(key(item), len(order))))


def repair(
    doc: BriefDocument, report: ValidationReport, rctx: RepairContext, attempt: int
) -> tuple[BriefDocument, list[str]]:
    """One repair pass. Returns the repaired brief and a plain log of what was done."""
    violations = [v for check in report.failing for v in check.violations]
    log: list[str] = []

    figure_keys = {
        v.locator.kpi_key for v in violations if v.fix == "rebuild_figure" and v.locator.kpi_key
    }
    option_keys = {
        v.locator.kpi_key for v in violations if v.fix == "regenerate_options" and v.locator.kpi_key
    }
    sections = any(v.fix == "rebuild_sections" for v in violations)

    # 1. figures, rebuilt from the engine
    kpis = {f.key: f for f in doc.kpis}
    flags_changed = False
    for key in sorted(figure_keys):
        authoritative = rctx.figures.get(key)
        if authoritative is None:
            continue
        previous = kpis.get(key)
        if previous is None or previous.flags != authoritative.flags:
            flags_changed = True
        sections = sections or previous is None  # a figure came back, so the summary needs it
        kpis[key] = authoritative
        log.append(f"Rebuilt figure {key} from the KPI engine")
    figures = _in_plan_order(rctx.plan, kpis.values(), lambda f: f.key)

    # 2. option sets, drafted again with the diagnosis
    sets = {s.kpi_key: s for s in doc.option_sets}
    for key in sorted(option_keys):
        figure = kpis.get(key) or rctx.figures.get(key)
        if figure is None:
            continue
        diagnosis = " ".join(
            v.diagnosis
            for v in violations
            if v.fix == "regenerate_options" and v.locator.kpi_key == key
        )
        guide = rctx.frameworks.drafting_context(figure.framework) if rctx.frameworks else None
        sets[key] = draft_option_set(
            rctx.model, figure, attempt=attempt, diagnosis=diagnosis, inject=(), framework=guide
        )
        log.append(f"Regenerated options for {key}")
    option_sets: tuple[OptionSet, ...] = _in_plan_order(
        rctx.plan, sets.values(), lambda s: s.kpi_key
    )

    # 3. the composer's own sections, derived again from the figures
    updates: dict = {"kpis": figures, "option_sets": option_sets}
    if sections or flags_changed:
        health_domains: tuple[Domain, ...] = (*rctx.plan.domains, Domain.REFERENCE)
        updates["summary"] = build_summary(figures)
        pending = rctx.frameworks.pending_labels() if rctx.frameworks else ()
        updates["assumptions"] = build_assumptions(figures, rctx.health, health_domains, pending)
        updates["data_health"] = build_health_notes(rctx.health, health_domains)
        log.append("Rebuilt the summary, assumptions and data health sections")

    # 4. a false claim of approval
    if any(v.fix == "reset_status" for v in violations):
        updates["claims_status"] = "draft"
        log.append("Reset the brief status to draft")

    return doc.model_copy(update=updates), log


def validate_and_repair(
    doc: BriefDocument,
    vctx: ValidationContext,
    rctx: RepairContext,
    max_attempts: int = 3,
) -> tuple[BriefDocument, ValidationReport, list[ValidationReport]]:
    """Validate, repair, validate again, at most `max_attempts` looks in all.

    Returns the final brief, the final report (passed or not) and every report along the way.
    A report that has not passed means escalation: the brief goes to a person with its diagnosis.
    """
    attempt = 1
    report = validate(doc, vctx, attempt)
    history = [report]
    while not report.passed and attempt < max_attempts:
        attempt += 1
        doc, _ = repair(doc, report, rctx, attempt)
        report = validate(doc, vctx, attempt)
        history.append(report)
    return doc, report, history
