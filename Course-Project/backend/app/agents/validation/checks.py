"""The nine validation checks (docs/SPEC.md section 7). Deterministic. A model may add a signal,
never the gate.

Each check returns violations with a locator (kpi_key, option_id or section) and a `fix` hint, so
a repair can regenerate only the failing part (Lab 10) and the approver can see exactly what is
wrong. Checks read the brief itself, including the figures frozen inside it, so a brief carrying a
corrupted figure is judged on that figure.
"""

import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass

from app.agents.compose import fact_figure
from app.agents.models import (
    BriefDocument,
    FactFigure,
    Fix,
    Locator,
    Plan,
    Violation,
)
from app.agents.tokens import Ref, RenderContext, lint_numbers, parse_tokens, unresolved_refs
from app.domain.enums import ACTUAL_STATUSES, FactStatus, KpiStatus
from app.domain.models import KpiDefinition, MetricFact, Publication, SourceSystem
from app.kpi.engine import judge

UNIQUE_PUBLICATIONS = "unique_publications()"
MIN_OPTIONS, MAX_OPTIONS = 2, 3

# What a text must not say about a figure that is not final, and what it must say instead
_FINALITY_WORDS = re.compile(
    r"\b(?:actual|actuals|final|finalised|finalized|confirmed|audited|achieved|secured|"
    r"realised|realized)\b",
    re.IGNORECASE,
)
_STATUS_WORDS = {
    FactStatus.PROVISIONAL: re.compile(r"\bprovisional\b", re.IGNORECASE),
    FactStatus.FORECAST: re.compile(r"\bforecast\b", re.IGNORECASE),
    FactStatus.PENDING_RECONCILIATION: re.compile(
        r"\b(?:pending|unreconciled|reconcil\w*)\b", re.IGNORECASE
    ),
}


@dataclass(frozen=True)
class ValidationContext:
    plan: Plan
    facts: Mapping[int, MetricFact]
    sources: Mapping[int, SourceSystem]
    publications: Sequence[Publication]
    definitions: Mapping[str, KpiDefinition]
    approval_present: bool = False


class _LazyFacts(Mapping[int, FactFigure]):
    """Fact figures built on demand, since most checks never look at most of the records."""

    def __init__(self, facts: Mapping[int, MetricFact]) -> None:
        self._facts = facts

    def __getitem__(self, key: int) -> FactFigure:
        return fact_figure(self._facts[key])

    def __iter__(self):
        return iter(self._facts)

    def __len__(self) -> int:
        return len(self._facts)


def render_context(doc: BriefDocument, ctx: ValidationContext) -> RenderContext:
    return RenderContext(kpis={f.key: f for f in doc.kpis}, facts=_LazyFacts(ctx.facts))


def authored_texts(doc: BriefDocument) -> Iterator[tuple[Locator, str]]:
    """Every string a model or the composer wrote, with where it sits."""
    for item in doc.summary:
        yield Locator(kpi_key=item.kpi_key, section="summary"), item.headline
    for note in doc.assumptions:
        yield Locator(section="assumptions"), note.text
    for option_set in doc.option_sets:
        for option in option_set.options:
            where = Locator(kpi_key=option_set.kpi_key, option_id=option.id)
            yield where, option.title
            yield where, option.description
            for line in (*option.assumptions, *option.risks, *option.trade_offs):
                yield where, line


def _raw(ref: Ref) -> str:
    return "{{" + f"{ref.kind}:{ref.key}" + ("" if ref.field == "value" else f".{ref.field}") + "}}"


def _text_fix(where: Locator) -> Fix:
    """A fault in an option's own text means regenerating that option set. Elsewhere, the
    composer's sections are simply rebuilt."""
    return "regenerate_options" if where.option_id else "rebuild_sections"


def _violation(fix: Fix, where: Locator, message: str, diagnosis: str) -> Violation:
    return Violation(locator=where, message=message, diagnosis=diagnosis, fix=fix)


# --- V1 ------------------------------------------------------------------------------------
def v1_figures_cite_sources(doc: BriefDocument, ctx: ValidationContext) -> list[Violation]:
    context = render_context(doc, ctx)
    found: dict[tuple, Violation] = {}
    for where, text in authored_texts(doc):
        fragments = lint_numbers(text)
        if fragments:
            quoted = ", ".join(repr(f) for f in fragments)
            found[("lint", where, quoted)] = _violation(
                _text_fix(where),
                where,
                f"Figure written by hand: {quoted}",
                f"Found {', '.join(fragments)} outside a reference token. Figures may only be "
                "written as {{kpi:KEY}} or {{fact:ID}} tokens, so that each one resolves to a source.",
            )
        for ref in unresolved_refs(text, context):
            found[("unresolved", where, _raw(ref))] = _violation(
                _text_fix(where),
                where,
                f"The reference {_raw(ref)} does not resolve to a known KPI or record",
                "Every reference token must name a KPI in this brief or a source record that exists.",
            )
        for part in parse_tokens(text):
            if not isinstance(part, Ref):
                continue
            if part.kind == "kpi":
                figure = context.kpis.get(part.key)
                if figure and figure.value is not None and not figure.input_fact_ids:
                    found[("nosrc", part.key)] = _violation(
                        "rebuild_figure",
                        Locator(kpi_key=part.key),
                        f"{part.key} is cited but rests on no source records",
                        "A figure with no source records cannot be cited. Rebuild it from the KPI engine.",
                    )
            elif part.key.isdigit() and int(part.key) in ctx.facts:
                if not ctx.facts[int(part.key)].source_ref:
                    found[("nosrc-fact", part.key)] = _violation(
                        _text_fix(where),
                        where,
                        f"Record {part.key} has no source reference",
                        "Every record cited must carry its source reference.",
                    )
    return list(found.values())


# --- V2 ------------------------------------------------------------------------------------
def v2_assumptions_stated(doc: BriefDocument, ctx: ValidationContext) -> list[Violation]:
    found: list[Violation] = []
    for option_set in doc.option_sets:
        for option in option_set.options:
            if not any(a.strip() for a in option.assumptions):
                found.append(
                    _violation(
                        "regenerate_options",
                        Locator(kpi_key=option_set.kpi_key, option_id=option.id),
                        f"Option {option.id} states no assumptions",
                        "Every option must say what it assumes to be true.",
                    )
                )

    stated = {(a.kind, a.dept_code) for a in doc.assumptions}
    section = Locator(section="assumptions")

    def missing(kind: str, dept: str | None, message: str) -> None:
        if (kind, dept) not in stated:
            found.append(
                _violation(
                    "rebuild_sections",
                    section,
                    message,
                    f"{message}. State it in the assumptions section.",
                )
            )

    if any(f.as_of is not None for f in doc.kpis):
        missing("as_of", None, "The brief does not say how fresh its figures are")
    if any(f.placeholder for f in doc.kpis):
        missing(
            "placeholder",
            None,
            "The brief does not say its definitions and targets are placeholders",
        )
    for figure in doc.kpis:
        flags = figure.flags
        for kind, depts in (
            ("stale", flags.stale_departments),
            ("missing", flags.missing_departments),
            ("excluded", flags.excluded_departments),
            ("undefined", flags.undefined_departments),
        ):
            for dept in depts:
                missing(
                    kind,
                    dept,
                    f"{kind.capitalize()} department {dept} is not stated for {figure.name}",
                )
    return found


# --- V3 ------------------------------------------------------------------------------------
def v3_risks_and_trade_offs(doc: BriefDocument, ctx: ValidationContext) -> list[Violation]:
    found: list[Violation] = []
    for option_set in doc.option_sets:
        for option in option_set.options:
            for name, lines in (("risks", option.risks), ("trade-offs", option.trade_offs)):
                if not any(line.strip() for line in lines):
                    found.append(
                        _violation(
                            "regenerate_options",
                            Locator(kpi_key=option_set.kpi_key, option_id=option.id),
                            f"Option {option.id} lists no {name}",
                            f"Every option must list its {name}. Regenerate this option with them.",
                        )
                    )
    return found


# --- V4 ------------------------------------------------------------------------------------
def v4_non_final_not_presented_as_final(
    doc: BriefDocument, ctx: ValidationContext
) -> list[Violation]:
    found: list[Violation] = []
    for where, text in authored_texts(doc):
        for part in parse_tokens(text):
            if not (isinstance(part, Ref) and part.kind == "fact" and part.key.isdigit()):
                continue
            fact = ctx.facts.get(int(part.key))
            if fact is None or fact.status in ACTUAL_STATUSES:
                continue
            problems = []
            claimed = _FINALITY_WORDS.search(text)
            if claimed:
                problems.append(f"calls it '{claimed.group().lower()}'")
            if not _STATUS_WORDS[fact.status].search(text):
                problems.append(f"never says it is {fact.status.value.replace('_', ' ')}")
            if problems:
                found.append(
                    _violation(
                        _text_fix(where),
                        where,
                        f"Record {fact.id} is {fact.status.value.replace('_', ' ')} but the text "
                        f"{' and '.join(problems)}",
                        "A provisional, forecast or unreconciled figure must be described as exactly "
                        "that, and never as actual, final or confirmed.",
                    )
                )
    return found


# --- V5 ------------------------------------------------------------------------------------
def v5_no_action_without_approval(doc: BriefDocument, ctx: ValidationContext) -> list[Violation]:
    if doc.claims_status in ("approved", "published") and not ctx.approval_present:
        return [
            _violation(
                "reset_status",
                Locator(section="status"),
                f"The brief says it is {doc.claims_status} but there is no approval record",
                "A brief stays a draft until an authorised person approves it. Reset it to draft.",
            )
        ]
    return []


# --- V6 ------------------------------------------------------------------------------------
def v6_definitions_and_no_masked_misses(
    doc: BriefDocument, ctx: ValidationContext
) -> list[Violation]:
    found: list[Violation] = []
    for figure in doc.kpis:
        where = Locator(kpi_key=figure.key)
        definition = ctx.definitions.get(figure.key)
        if definition is None or not figure.definition_active or not definition.active:
            found.append(
                _violation(
                    "rebuild_figure",
                    where,
                    f"{figure.key} has no active definition",
                    "Only active, defined KPIs may appear in a brief.",
                )
            )
            continue
        if figure.kpi_version != definition.version:
            found.append(
                _violation(
                    "rebuild_figure",
                    where,
                    f"{figure.key} used an older definition version",
                    "Rebuild the figure from the current definition.",
                )
            )
        if not figure.placeholder and not figure.definition_approved:
            found.append(
                _violation(
                    "rebuild_figure",
                    where,
                    f"{figure.key} is not an approved definition",
                    "Only approved definitions may be used, or the definition must be marked as a placeholder.",
                )
            )

        if figure.value is None or figure.target is None:
            expected = KpiStatus.UNDEFINED
        else:
            band = figure.band_pct if figure.band_pct is not None else definition.at_risk_band_pct
            expected, _, _ = judge(figure.value, figure.target, figure.higher_is_better, band)
        if figure.status is not expected:
            found.append(
                _violation(
                    "rebuild_figure",
                    where,
                    f"{figure.key} is marked {figure.status.value} but its unrounded figures "
                    f"say {expected.value}",
                    "Status must be decided on the unrounded value, never on a rounded one, so a "
                    "miss cannot be hidden. Rebuild the figure from the KPI engine.",
                )
            )
    return found


# --- V7 ------------------------------------------------------------------------------------
def v7_drilldown_traceable(doc: BriefDocument, ctx: ValidationContext) -> list[Violation]:
    found: list[Violation] = []
    for figure in doc.kpis:
        if figure.value is None:
            continue
        where = Locator(kpi_key=figure.key)
        if not figure.input_fact_ids:
            found.append(
                _violation(
                    "rebuild_figure",
                    where,
                    f"{figure.key} lists no source records",
                    "Every KPI must resolve to the records it was computed from. Rebuild it from the KPI engine.",
                )
            )
            continue
        for fact_id in figure.input_fact_ids:
            fact = ctx.facts.get(fact_id)
            if fact is None:
                found.append(
                    _violation(
                        "rebuild_figure",
                        where,
                        f"{figure.key} cites record {fact_id}, which does not exist",
                        "A source record that cannot be found cannot be traced.",
                    )
                )
            elif not fact.source_ref or fact.source_system_id not in ctx.sources:
                found.append(
                    _violation(
                        "rebuild_figure",
                        where,
                        f"Record {fact_id} behind {figure.key} has no source",
                        "Every record must name its source system and reference.",
                    )
                )
    return found


# --- V8 ------------------------------------------------------------------------------------
def v8_coverage(doc: BriefDocument, ctx: ValidationContext) -> list[Violation]:
    found: list[Violation] = []
    present = {f.key for f in doc.kpis}
    summarised = {s.kpi_key for s in doc.summary}
    for key in ctx.plan.kpi_keys:
        if key not in present or key not in summarised:
            found.append(
                _violation(
                    "rebuild_figure",
                    Locator(kpi_key=key),
                    f"{key} is in the locked plan but missing from the brief",
                    "Every KPI in the locked plan must appear in the brief.",
                )
            )

    needs_options = [
        f
        for f in doc.kpis
        if f.key in ctx.plan.kpi_keys
        and (
            f.status is not KpiStatus.UNDEFINED
            if ctx.plan.options_for == "all"
            else f.status in (KpiStatus.MISSED, KpiStatus.AT_RISK)
        )
    ]
    option_counts = {s.kpi_key: len(s.options) for s in doc.option_sets}
    for figure in needs_options:
        count = option_counts.get(figure.key, 0)
        if not MIN_OPTIONS <= count <= MAX_OPTIONS:
            found.append(
                _violation(
                    "regenerate_options",
                    Locator(kpi_key=figure.key),
                    f"{figure.key} is {figure.status.value} and has {count} options, "
                    f"it needs {MIN_OPTIONS} or {MAX_OPTIONS}",
                    "Every off-target KPI needs two or three options with their risks and trade-offs.",
                )
            )

    noted = {(n.dept_code, n.domain, n.state) for n in doc.data_health}
    noted_non_final = {(n.dept_code, n.domain) for n in doc.data_health if n.non_final}
    section = Locator(section="data_health")
    for figure in doc.kpis:
        for state, depts in (
            ("stale", figure.flags.stale_departments),
            ("missing", figure.flags.missing_departments),
        ):
            for dept in depts:
                if (dept, figure.domain, state) not in noted:
                    found.append(
                        _violation(
                            "rebuild_sections",
                            section,
                            f"{state.capitalize()} department {dept} is not flagged in the data health section",
                            "Stale and missing departments must be flagged, never left out.",
                        )
                    )
        for dept in figure.flags.excluded_departments:
            if (dept, figure.domain) not in noted_non_final:
                found.append(
                    _violation(
                        "rebuild_sections",
                        section,
                        f"Excluded department {dept} is not flagged in the data health section",
                        "A department kept out because of a non-final figure must be flagged.",
                    )
                )
    return found


# --- V9 ------------------------------------------------------------------------------------
def v9_no_double_counting(doc: BriefDocument, ctx: ValidationContext) -> list[Violation]:
    found: list[Violation] = []
    for figure in doc.kpis:
        term = next((t for t in figure.inputs if t.label == UNIQUE_PUBLICATIONS), None)
        if term is None:
            continue
        included = set(figure.included_departments)
        distinct = len(
            {
                p.dedup_key
                for p in ctx.publications
                if p.period_year == figure.period_year
                and p.status in ACTUAL_STATUSES
                and included & set(p.dept_codes)
            }
        )
        if term.value != distinct:
            found.append(
                _violation(
                    "rebuild_figure",
                    Locator(kpi_key=figure.key),
                    f"{figure.key} counts {term.value} publications but there are {distinct} distinct papers",
                    "A paper shared by two departments counts once for the institution and is credited "
                    "to each department. Rebuild the figure from the KPI engine.",
                )
            )
    return found


Check = Callable[[BriefDocument, ValidationContext], list[Violation]]

CHECKS: tuple[tuple[str, str, Check], ...] = (
    ("V1", "Every figure cites its source", v1_figures_cite_sources),
    ("V2", "Assumptions are stated explicitly", v2_assumptions_stated),
    ("V3", "Each option lists its risks and trade-offs", v3_risks_and_trade_offs),
    ("V4", "No non-final figure presented as final", v4_non_final_not_presented_as_final),
    ("V5", "No action without approval", v5_no_action_without_approval),
    ("V6", "Only approved definitions, no masked misses", v6_definitions_and_no_masked_misses),
    ("V7", "Drill-down is traceable", v7_drilldown_traceable),
    ("V8", "Coverage", v8_coverage),
    ("V9", "No double counting", v9_no_double_counting),
)
