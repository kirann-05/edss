"""The archive of prior briefs and what leadership decided (Lab 4, decision D20).

Run state is short term and belongs to one run. The archive is long term: past briefs, kept
apart so a draft in progress can never corrupt the baseline it is compared with. For a draft
under review it answers "have we seen this before, and what did we do about it?" by matching on
which KPIs were off target.

Seeded here from the closed years of the synthetic dataset, through the real engine. The pgvector
version adds embedding similarity on top of the same tags (CHECKLIST F5).
"""

from datetime import date, timedelta

from app.agents.compose import figure_from, off_target
from app.agents.llm import ChatModel
from app.agents.models import BriefDocument, KpiFigure
from app.agents.skills.options_skill import draft_option_set
from app.domain.enums import KpiStatus
from app.domain.models import Frozen
from app.governance.service import BriefVersion
from app.services.store import DataStore


class PriorBrief(Frozen):
    id: str
    period_year: str
    title: str
    decided_on: date
    decision: str  # what leadership did, in words
    off_target: dict[str, str]  # kpi key to its status at the time
    chosen: dict[str, str]  # kpi key to the title of the option leadership chose
    brief_id: str | None = None  # set for a report published in this system


class PriorMatch(Frozen):
    brief: PriorBrief
    matching_kpis: list[str]
    score: float
    reason: str


class Archive:
    def __init__(self, priors: list[PriorBrief]) -> None:
        self._priors = priors

    def all(self) -> list[PriorBrief]:
        return list(self._priors)

    def add(self, prior: PriorBrief) -> None:
        self._priors = [p for p in self._priors if p.id != prior.id] + [prior]

    def similar(
        self, doc: BriefDocument, limit: int = 3, exclude_brief: str | None = None
    ) -> list[PriorMatch]:
        """Prior briefs ranked by overlap in which KPIs were off target. Jaccard over the KPI keys."""
        now = {k.key for k in doc.kpis if k.status in (KpiStatus.MISSED, KpiStatus.AT_RISK)}
        matches = []
        for prior in self._priors:
            if exclude_brief is not None and prior.brief_id == exclude_brief:
                continue
            before = set(prior.off_target)
            union = now | before
            shared = sorted(now & before)
            if not union or not shared:
                continue
            same_status = [k for k in shared if prior.off_target[k] == _status_of(doc, k)]
            matches.append(
                PriorMatch(
                    brief=prior,
                    matching_kpis=shared,
                    score=round(len(shared) / len(union), 2),
                    reason=(
                        f"{len(shared)} of the same KPIs were off target"
                        + (f", {len(same_status)} with the same status" if same_status else "")
                    ),
                )
            )
        # best match first, and among equals the most recent decision
        return sorted(matches, key=lambda m: (-m.score, -m.brief.decided_on.toordinal()))[:limit]


def _status_of(doc: BriefDocument, key: str) -> str:
    return next(k.status.value for k in doc.kpis if k.key == key)


def seed_archive(store: DataStore, model: ChatModel) -> Archive:
    """One prior brief per closed year, built from that year's real engine results."""
    priors: list[PriorBrief] = []
    closed = [p for p in store.periods if p != store.current_period]
    for index, period in enumerate(reversed(closed), start=1):
        figures = []
        for definition in store.definitions:
            figures.append(figure_from(definition, store.result(definition.key, period)))
        needing: list[KpiFigure] = off_target(figures)
        chosen = {f.key: draft_option_set(model, f).options[0].title for f in needing}
        names = {f.key: f.name for f in figures}
        priors.append(
            PriorBrief(
                id=f"prior-{period}",
                period_year=period,
                title=f"Decision brief, {period}",
                decided_on=store.today - timedelta(days=365 * index - 30),
                decision=(
                    "Approved. Leadership chose: "
                    + "; ".join(f"{names[k]}: {v}" for k, v in chosen.items())
                    if chosen
                    else "Approved with no off-target KPIs."
                ),
                off_target={f.key: f.status.value for f in needing},
                chosen=chosen,
            )
        )
    return Archive(priors)


def prior_from_version(version: BriefVersion) -> PriorBrief:
    """A published report, kept as a prior for the briefs that come after it. The approval is of
    the whole brief, so it records the options put forward, not one chosen among them."""
    doc = version.document
    names = {k.key: k.name for k in doc.kpis}
    put_forward = [
        f"{names.get(s.kpi_key, s.kpi_key)}: {s.options[0].title}"
        for s in doc.option_sets
        if s.options
    ]
    edits = f", with {len(version.edits)} edits" if version.edits else ""
    return PriorBrief(
        id=f"report-v{version.version}",
        period_year=doc.period_year,
        title=f"{doc.title}, version {version.version}",
        decided_on=version.approved_at.date(),
        decision=f"Approved by {version.approved_by} as version {version.version}{edits}."
        + (f" Options put forward: {'; '.join(put_forward)}." if put_forward else ""),
        off_target={
            k.key: k.status.value
            for k in doc.kpis
            if k.status in (KpiStatus.MISSED, KpiStatus.AT_RISK)
        },
        chosen={},
        brief_id=version.brief_id,
    )
