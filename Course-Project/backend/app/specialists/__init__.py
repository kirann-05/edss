"""Framework specialists (Lab 13): one implementation, one pack of configuration per framework.

docs/SPEC.md section 9 reads Lab 13's "domain packs" as framework packs. A pack says what a
framework's options should weigh, and the drafting node hands that to the model in words, so the
options for a strategic-plan KPI are shaped by the strategic plan. Each option set records which
pack drafted it, which makes the specialist's part checkable.

Rule 12 decides what the NIRF and NAAC packs may hold today: nothing. They are registered, they
answer, and they say plainly that they wait for IQAC. The loader refuses a pending pack that gains
guidance, and the app refuses to start if a KPI is tagged with a pending framework.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from app.domain.enums import KpiFramework

MARKER = "PLACEHOLDER_PENDING_IQAC"
PACKS = Path(__file__).parent / "packs"


class PackError(ValueError):
    pass


@dataclass(frozen=True)
class Specialist:
    framework: KpiFramework
    label: str
    status: Literal["active", "pending_iqac"]
    note: str
    guidance: str
    consider: tuple[str, ...]

    @property
    def pending(self) -> bool:
        return self.status == "pending_iqac"

    def drafting_context(self) -> dict[str, Any]:
        """What the drafter is told about the framework. Words only, like everything it is told."""
        return {"framework": self.label, "guidance": self.guidance, "consider": list(self.consider)}


class SpecialistRegistry:
    def __init__(self, packs: Iterable[Specialist]) -> None:
        self._packs = {p.framework: p for p in packs}
        missing = set(KpiFramework) - set(self._packs)
        if missing:
            raise PackError(f"no pack for {', '.join(sorted(missing))}")

    def get(self, framework: KpiFramework) -> Specialist:
        return self._packs[framework]

    def pending(self) -> list[Specialist]:
        return [p for p in self._packs.values() if p.pending]

    # --- the FrameworkGuide the graph is handed (app/agents/frameworks.py) ---------------------
    def drafting_context(self, framework: KpiFramework) -> dict[str, Any]:
        pack = self.get(framework)
        if pack.pending:
            raise PackError(f"the {pack.label} pack waits for IQAC and cannot guide a draft")
        return pack.drafting_context()

    def pending_labels(self) -> tuple[str, ...]:
        return tuple(sorted(p.label for p in self.pending()))

    def check_definitions(self, frameworks_in_use: Iterable[KpiFramework]) -> None:
        """A KPI tagged with a pending framework would mean a definition nobody approved."""
        for framework in set(frameworks_in_use):
            if self.get(framework).pending:
                raise PackError(
                    f"a KPI is tagged {framework.value}, but the {framework.value} pack waits for "
                    "IQAC. Approve the pack before using its definitions (rule 12)"
                )


def _pack(raw: dict[str, Any], source: str) -> Specialist:
    try:
        framework = KpiFramework(raw["framework"])
        status = raw["status"]
        note = str(raw.get("note") or "")
        guidance = str(raw.get("guidance") or "").strip()
        consider = tuple(str(c) for c in raw.get("consider") or ())
        label = str(raw["label"])
    except (KeyError, ValueError) as error:
        raise PackError(f"{source}: {error}") from None
    if status not in ("active", "pending_iqac"):
        raise PackError(f"{source}: status must be active or pending_iqac, not {status!r}")
    if status == "pending_iqac" and (guidance or consider or MARKER not in note):
        raise PackError(
            f"{source}: a pending pack carries no guidance and no areas, and its note says {MARKER}"
        )
    if status == "active" and not guidance:
        raise PackError(f"{source}: an active pack needs guidance for the drafter")
    if any(ch.isdigit() for ch in guidance + "".join(consider)):
        raise PackError(f"{source}: guidance is words only, never a figure")
    return Specialist(framework, label, status, note, guidance, consider)


def load_registry(folder: Path = PACKS) -> SpecialistRegistry:
    files = sorted(folder.glob("*.yaml"))
    return SpecialistRegistry(_pack(yaml.safe_load(f.read_text()) or {}, f.name) for f in files)


SPECIALISTS = load_registry()
