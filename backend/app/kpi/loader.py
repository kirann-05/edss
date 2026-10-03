"""Load KPI definitions and targets from YAML (decision D8: definitions are data, not code).

The loader is strict on purpose. A typo, an unknown metric, a duplicate key, or a placeholder
that is not marked as one stops the load with the KPI named, so a bad definition can never
reach a leadership brief.
"""

from collections.abc import Collection
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from app.domain.enums import Domain, KpiFramework
from app.domain.models import KpiDefinition, KpiTarget
from app.kpi.catalogue import CATALOGUE
from app.kpi.formulas import FormulaError, parse_formula

PLACEHOLDER_MARKER = "PLACEHOLDER_PENDING_IQAC"
SEED_DIR = Path(__file__).parent / "definitions"

_ALLOWED = {
    "key", "name", "framework", "domain", "domain_tags", "formula", "unit",
    "higher_is_better", "version", "approved_by", "approved_on", "active", "placeholder",
    "display_precision", "at_risk_band_pct", "note",
}  # fmt: skip


class DefinitionError(ValueError):
    """A definition or target file is not acceptable."""


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def load_definitions(path: Path) -> list[KpiDefinition]:
    rows = yaml.safe_load(path.read_text())
    if not isinstance(rows, list):
        raise DefinitionError(f"{path.name}: expected a list of KPI definitions")

    definitions: list[KpiDefinition] = []
    seen: set[str] = set()
    for row in rows:
        key = row.get("key", "<no key>")
        try:
            unknown = set(row) - _ALLOWED
            if unknown:
                raise DefinitionError(f"unknown field(s) {sorted(unknown)}")
            if key in seen:
                raise DefinitionError("duplicate key")
            seen.add(key)

            domain = Domain(row["domain"])
            tags = tuple(Domain(t) for t in row.get("domain_tags", [domain]))
            placeholder = bool(row.get("placeholder", True))
            note = row.get("note")
            if placeholder and PLACEHOLDER_MARKER not in (note or ""):
                raise DefinitionError(
                    f"a placeholder definition must carry {PLACEHOLDER_MARKER} in its note (rule 12)"
                )
            definition = KpiDefinition(
                key=key,
                name=row["name"],
                framework=KpiFramework(row.get("framework", KpiFramework.STRATEGIC)),
                domain=domain,
                domain_tags=tags,
                formula=row["formula"],
                unit=row["unit"],
                higher_is_better=row.get("higher_is_better", True),
                version=row.get("version", 1),
                approved_by=row.get("approved_by"),
                approved_on=row.get("approved_on"),
                active=row.get("active", True),
                placeholder=placeholder,
                display_precision=row.get("display_precision", 1),
                at_risk_band_pct=_decimal(row.get("at_risk_band_pct", 2)),
                note=note,
            )
            parse_formula(definition.formula, CATALOGUE)
        except (DefinitionError, FormulaError, KeyError, ValueError) as error:
            raise DefinitionError(f"{path.name}: KPI {key}: {error}") from error
        definitions.append(definition)
    return definitions


def load_targets(path: Path, known_keys: Collection[str]) -> list[KpiTarget]:
    raw = yaml.safe_load(path.read_text())
    source_doc = raw["source_doc"]
    targets: list[KpiTarget] = []
    for key, by_period in raw["targets"].items():
        if key not in known_keys:
            raise DefinitionError(f"{path.name}: target for unknown KPI {key}")
        for period, value in by_period.items():
            targets.append(
                KpiTarget(
                    kpi_key=key,
                    period_year=str(period),
                    target_value=_decimal(value),
                    framework=KpiFramework.STRATEGIC,
                    source_doc=source_doc,
                    placeholder=source_doc == PLACEHOLDER_MARKER,
                )
            )
    return targets


def load_seed_definitions() -> list[KpiDefinition]:
    return load_definitions(SEED_DIR / "placeholder_kpis.yaml")


def load_seed_targets() -> list[KpiTarget]:
    keys = {d.key for d in load_seed_definitions()}
    return load_targets(SEED_DIR / "placeholder_targets.yaml", keys)
