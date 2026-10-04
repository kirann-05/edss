"""The archive of prior briefs, searched by meaning with pgvector (Lab 4, CHECKLIST L5h).

The same question as the in-memory archive, "have we seen this before, and what did we do about
it?", answered by nearness of embeddings instead of only by shared KPI keys. Each prior is
embedded once from its words (title, the KPIs off target with their status, what leadership
chose) and kept with exactly the text that was embedded. A draft is embedded the same way and
the nearest priors come back by cosine similarity, still saying which KPIs they share.
"""

from typing import Any

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert

from app.agents.models import BriefDocument
from app.db import schema as t
from app.domain.enums import KpiStatus
from app.services.archive import PriorBrief, PriorMatch


def prior_text(prior: PriorBrief, names: dict[str, str]) -> str:
    off = "; ".join(f"{names.get(k, k)} {s.replace('_', ' ')}" for k, s in prior.off_target.items())
    chosen = "; ".join(prior.chosen.values())
    return (
        f"{prior.title}. Off target: {off or 'nothing'}. Leadership chose: {chosen or 'nothing'}."
    )


def draft_text(doc: BriefDocument) -> str:
    off = "; ".join(
        f"{k.name} {k.status.value.replace('_', ' ')}"
        for k in doc.kpis
        if k.status in (KpiStatus.MISSED, KpiStatus.AT_RISK)
    )
    options = "; ".join(o.title for s in doc.option_sets for o in s.options)
    return f"{doc.title}. Off target: {off or 'nothing'}. Options: {options or 'none'}."


class DbArchive:
    def __init__(self, engine: Engine, embedder: Any, names: dict[str, str]) -> None:
        self._engine, self._embedder, self._names = engine, embedder, names

    def index(self, priors: list[PriorBrief]) -> None:
        """Embed and keep each prior, replacing an earlier embedding of the same one."""
        texts = [prior_text(p, self._names) for p in priors]
        vectors = self._embedder.embed(texts, "document") if texts else []
        with self._engine.begin() as conn:
            for prior, text, vector in zip(priors, texts, vectors, strict=True):
                values = {
                    "ref": prior.id, "content": text, "record": prior.model_dump(mode="json"),
                    "embedding": vector, "tags": sorted(prior.off_target),
                }  # fmt: skip
                statement = insert(t.brief_embedding).values(**values)
                conn.execute(
                    statement.on_conflict_do_update(
                        index_elements=["ref"],
                        set_={k: statement.excluded[k] for k in values if k != "ref"},
                    )
                )

    def all(self) -> list[PriorBrief]:
        with self._engine.connect() as conn:
            records = conn.execute(
                select(t.brief_embedding.c.record).order_by(t.brief_embedding.c.ref)
            ).scalars()
            return [PriorBrief.model_validate(r) for r in records]

    def similar(self, doc: BriefDocument, limit: int = 3) -> list[PriorMatch]:
        (query,) = self._embedder.embed([draft_text(doc)], "query")
        distance = t.brief_embedding.c.embedding.cosine_distance(query)
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(t.brief_embedding.c.record, distance.label("distance"))
                .order_by(distance)
                .limit(limit)
            ).all()
        now = {
            k.key: k.status.value
            for k in doc.kpis
            if k.status in (KpiStatus.MISSED, KpiStatus.AT_RISK)
        }
        matches = []
        for row in rows:
            prior = PriorBrief.model_validate(row.record)
            shared = sorted(set(now) & set(prior.off_target))
            similarity = round(1 - float(row.distance), 2)
            same = [k for k in shared if prior.off_target[k] == now[k]]
            matches.append(
                PriorMatch(
                    brief=prior,
                    matching_kpis=shared,
                    score=similarity,
                    reason=(
                        f"close in meaning ({similarity:.2f})"
                        + (f", {len(shared)} of the same KPIs were off target" if shared else "")
                        + (f", {len(same)} with the same status" if same else "")
                    ),
                )
            )
        return matches
