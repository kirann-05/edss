"""Numbers by reference (docs/ARCHITECTURE.md principle 2, rule 1).

Text written by a model may refer to a figure only as a token, {{kpi:KEY}} or {{fact:ID}}.
This module turns tokens into figures, using the engine's results, and lints everything else:

  * a token is replaced here, in code, so the model never writes, computes or rounds a figure
  * any digit left over outside a token is a violation (check V1)
  * so is a spelled-out number (decision D21), because "three departments" is a figure too

A KPI token can name a field: {{kpi:PL_PCT}} or .value, .target, .gap (the gap to target in
words) and .status.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from app.agents.figures import format_number, format_variance, format_with_unit
from app.agents.models import FactFigure, KpiFigure

KPI_FIELDS = ("value", "target", "gap", "status")
_STATUS_WORDS = {"met": "Met", "at_risk": "At risk", "missed": "Missed", "undefined": "Undefined"}

_TOKEN = re.compile(r"\{\{\s*(kpi|fact)\s*:\s*([A-Za-z0-9_]+)(?:\.([A-Za-z]+))?\s*\}\}")


@dataclass(frozen=True)
class Ref:
    kind: Literal["kpi", "fact"]
    key: str
    field: str = "value"


@dataclass(frozen=True)
class RenderContext:
    kpis: Mapping[str, KpiFigure]
    facts: Mapping[int, FactFigure]


class Segment(BaseModel):
    """A piece of rendered text. A ref segment is a figure the UI makes clickable and badged."""

    t: Literal["text", "ref"]
    text: str | None = None
    kind: Literal["kpi", "fact"] | None = None
    key: str | None = None
    field: str | None = None
    display: str | None = None
    status: str | None = None  # the KPI's status, or the record's, so a badge can be drawn
    unresolved: bool = False


def parse_tokens(text: str) -> list[str | Ref]:
    parts: list[str | Ref] = []
    cursor = 0
    for match in _TOKEN.finditer(text):
        if match.start() > cursor:
            parts.append(text[cursor : match.start()])
        kind, key, field = match.group(1), match.group(2), match.group(3)
        parts.append(Ref(kind, key, field or "value"))  # type: ignore[arg-type]
        cursor = match.end()
    if cursor < len(text):
        parts.append(text[cursor:])
    return parts or [text]


def _resolve(ref: Ref, context: RenderContext) -> tuple[str, str | None] | None:
    """The display text and status for a reference, or None when it does not resolve."""
    if ref.kind == "kpi":
        kpi = context.kpis.get(ref.key)
        if kpi is None or ref.field not in KPI_FIELDS:
            return None
        if ref.field == "value":
            text = format_with_unit(kpi.value, kpi.precision, kpi.unit)
        elif ref.field == "target":
            text = format_with_unit(kpi.target, kpi.precision, kpi.unit)
        elif ref.field == "gap":
            text = format_variance(kpi.variance_abs, kpi.precision, kpi.unit)
        else:
            text = _STATUS_WORDS[kpi.status.value]
        return text, kpi.status.value

    if not ref.key.isdigit() or ref.field != "value":
        return None
    fact = context.facts.get(int(ref.key))
    if fact is None:
        return None
    places = 0 if fact.value == fact.value.to_integral_value() else 2
    return f"{format_number(fact.value, places)} {fact.unit}", fact.status.value


def render_segments(text: str, context: RenderContext) -> list[Segment]:
    segments: list[Segment] = []
    for part in parse_tokens(text):
        if isinstance(part, str):
            segments.append(Segment(t="text", text=part))
            continue
        resolved = _resolve(part, context)
        raw = f"{{{{{part.kind}:{part.key}{'' if part.field == 'value' else '.' + part.field}}}}}"
        if resolved is None:
            segments.append(
                Segment(
                    t="ref",
                    kind=part.kind,
                    key=part.key,
                    field=part.field,
                    display=raw,
                    unresolved=True,
                )
            )
        else:
            display, status = resolved
            segments.append(
                Segment(
                    t="ref",
                    kind=part.kind,
                    key=part.key,
                    field=part.field,
                    display=display,
                    status=status,
                )
            )
    return segments


def render_text(text: str, context: RenderContext) -> str:
    return "".join(
        s.text or "" if s.t == "text" else s.display or "" for s in render_segments(text, context)
    )


def unresolved_refs(text: str, context: RenderContext) -> list[Ref]:
    return [p for p in parse_tokens(text) if isinstance(p, Ref) and _resolve(p, context) is None]


# --- the number lint (check V1) ----------------------------------------------------------------
# Labels that name a period or a date are not figures: 2025-26, 2026-09-21, Q3, S2
_ALLOWED = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{4}-\d{2}\b"),
    re.compile(r"\bQ[1-4]\b"),
    re.compile(r"\bS[12]\b"),
]
_DIGITS = re.compile(r"\d+(?:[.,]\d+)*")
_NUMBER_WORDS = re.compile(
    r"\b(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|"
    r"ninety|hundred|thousand|lakh|crore|million|billion|half|dozen|double|triple|twice|thrice)\b",
    re.IGNORECASE,
)
# "one" is also a pronoun ("one of the departments", "no one") and "zero" is the concept the
# caveats are about ("never counted as zero"). Each counts as a figure only when followed by
# something countable.
_ONE_AS_COUNT = re.compile(
    r"\b(?:one|zero)\s+(?:percent|per\s*cent|point|points|department|departments|lakh|crore|student|"
    r"students|faculty|paper|papers|publication|publications|kpi|kpis|quarter|year|years|"
    r"semester|offer|offers|grant|grants)\b",
    re.IGNORECASE,
)


def lint_numbers(text: str) -> list[str]:
    """Figures a model wrote by hand: digits or number words outside a token. Empty means clean."""
    cleaned = _TOKEN.sub(" ", text)
    for allowed in _ALLOWED:
        cleaned = allowed.sub(" ", cleaned)
    found = [(m.start(), m.group()) for m in _DIGITS.finditer(cleaned)]
    found += [(m.start(), m.group()) for m in _NUMBER_WORDS.finditer(cleaned)]
    found += [(m.start(), m.group().split()[0]) for m in _ONE_AS_COUNT.finditer(cleaned)]
    return [fragment for _, fragment in sorted(found)]
