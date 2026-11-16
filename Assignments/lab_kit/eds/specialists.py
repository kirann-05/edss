"""
Lab 13 - Discipline-Specific Agents: pluggable domain specialists so
outputs match the specific style and constraints of each case.

    specialist = registry.get(domain)
    out = specialist.generate(item)
    GenerationAgent.use(specialist)

For the Executive Decision Support System, the "domain variant" that
matters most is which accreditation/strategic framework's KPI pack is
in force for this review cycle. Two illustrative packs are provided
below; register more via `registry.register(...)` without touching
`KPIAgent`.
"""

from __future__ import annotations

import copy
from typing import Any, Dict


class KPISpecialist:
    """Base interface every KPI specialist pack must implement."""

    label = "base"

    def apply_kpi_pack(self, kpi_defs: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class NAACWeightedSpecialist(KPISpecialist):
    """Tightens targets toward NAAC's typical accreditation-cycle
    expectations (illustrative values -- replace with your institution's
    actual approved NAAC targets)."""

    label = "naac_weighted"

    def apply_kpi_pack(self, kpi_defs: Dict[str, Any]) -> Dict[str, Any]:
        out = copy.deepcopy(kpi_defs)
        if "institution_pass_percentage" in out:
            out["institution_pass_percentage"]["target"] = 92.0
        if "institution_co_po_attainment" in out:
            out["institution_co_po_attainment"]["target"] = 0.80
        return out


class NIRFWeightedSpecialist(KPISpecialist):
    """Tightens targets toward NIRF ranking-band expectations
    (illustrative values -- replace with your institution's actual
    approved NIRF targets)."""

    label = "nirf_weighted"

    def apply_kpi_pack(self, kpi_defs: Dict[str, Any]) -> Dict[str, Any]:
        out = copy.deepcopy(kpi_defs)
        if "institution_publications_per_faculty" in out:
            out["institution_publications_per_faculty"]["target"] = 1.5
        if "institution_placement_percentage" in out:
            out["institution_placement_percentage"]["target"] = 88.0
        return out


class SpecialistRegistry:
    def __init__(self):
        self._specialists: Dict[str, KPISpecialist] = {}

    def register(self, specialist: KPISpecialist) -> None:
        self._specialists[specialist.label] = specialist

    def get(self, label: str) -> KPISpecialist:
        if label not in self._specialists:
            raise KeyError(f"No specialist registered under '{label}'. "
                            f"Known: {list(self._specialists)}")
        return self._specialists[label]

    def known(self):
        return list(self._specialists)


def default_registry() -> SpecialistRegistry:
    registry = SpecialistRegistry()
    registry.register(NAACWeightedSpecialist())
    registry.register(NIRFWeightedSpecialist())
    return registry
