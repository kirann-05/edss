"""L5h: prior briefs embedded with pgvector and found again by meaning (Lab 4)."""

import re
from datetime import date

import httpx2
import pytest
from sqlalchemy import create_engine, text

from app.db.archive_store import DbArchive
from app.db.embeddings import HashingEmbedder, OllamaEmbedder
from app.db.urls import app_url
from app.services.archive import PriorBrief

pytestmark = pytest.mark.db

NAMES = {
    "PL_PCT": "Placement percentage",
    "RS_PUB_PF": "Publications per faculty",
    "FN_UTIL": "Budget utilisation",
}


def prior(ref, off, chosen):
    return PriorBrief(
        id=ref, period_year="2024-25", title=f"Decision brief {ref}", decided_on=date(2025, 9, 1),
        decision="Approved.", off_target=off, chosen=chosen,
    )  # fmt: skip


@pytest.fixture(scope="module")
def archive(migrated, scratch_db):
    engine = create_engine(app_url(database=scratch_db))
    store = DbArchive(engine, HashingEmbedder(), NAMES)
    store.index([
        prior("prior-placement", {"PL_PCT": "missed"}, {"PL_PCT": "Intensify pre-placement training"}),
        prior("prior-research", {"RS_PUB_PF": "missed"}, {"RS_PUB_PF": "Seed grants for writing"}),
        prior("prior-finance", {"FN_UTIL": "at_risk"}, {"FN_UTIL": "Review the spending plan"}),
    ])  # fmt: skip
    yield store
    engine.dispose()


def test_each_prior_is_kept_with_exactly_the_words_that_were_embedded_and_no_figure(
    archive, migrated
):
    with migrated.connect() as conn:
        rows = conn.execute(
            text("select ref, content from brief_embedding where ref like 'prior-%'")
        ).all()
    assert {r.ref for r in rows} >= {"prior-placement", "prior-research", "prior-finance"}
    for row in rows:
        without_years = re.sub(r"\b20\d\d-\d\d\b", "", row.content)
        assert not any(c.isdigit() for c in without_years), row.content


def test_the_nearest_prior_comes_back_first(archive, connector, plan):
    from app.agents.models import BriefDocument
    from tests.mcp_connector.test_swap import run_graph

    placement_only = plan.model_copy(
        update={"domains": (plan.domains[2],), "kpi_keys": ("PL_PCT", "PL_AVG", "PL_INT")}
    )
    doc = BriefDocument.model_validate(run_graph(connector, placement_only)["brief"])
    matches = archive.similar(doc, limit=3)
    assert matches[0].brief.id == "prior-placement"
    assert matches[0].matching_kpis == ["PL_PCT"]
    assert [m.score for m in matches] == sorted((m.score for m in matches), reverse=True)
    assert matches[0].reason.startswith("close in meaning")


def test_the_search_uses_an_hnsw_index_for_cosine_distance(migrated):
    with migrated.connect() as conn:
        definition = conn.execute(
            text("select indexdef from pg_indexes where indexname = 'ix_brief_embedding_embedding'")
        ).scalar_one()
    assert "hnsw" in definition and "vector_cosine_ops" in definition


def test_embeddings_never_go_to_another_machine():
    with pytest.raises(ValueError, match="stay on this machine"):
        OllamaEmbedder("https://embeddings.example.com/v1", "nomic-embed-text")


def _ollama_up() -> bool:
    try:
        return httpx2.get("http://127.0.0.1:11434/api/version", timeout=1).status_code == 200
    except httpx2.HTTPError:
        return False


@pytest.mark.skipif(not _ollama_up(), reason="Ollama is not running")
def test_with_the_local_model_a_paraphrase_finds_the_right_prior(migrated, scratch_db):
    engine = create_engine(app_url(database=scratch_db))
    try:
        store = DbArchive(
            engine, OllamaEmbedder("http://127.0.0.1:11434/v1", "nomic-embed-text"), NAMES
        )
        store.index([
            prior("model-placement", {"PL_PCT": "missed"}, {"PL_PCT": "Intensify pre-placement training"}),
            prior("model-finance", {"FN_UTIL": "at_risk"}, {"FN_UTIL": "Review the spending plan"}),
        ])  # fmt: skip
        (query,) = store._embedder.embed(["fewer graduates got jobs than we aimed for"], "query")
        with engine.connect() as conn:
            nearest = conn.execute(
                text(
                    "select ref from brief_embedding where ref like 'model-%' order by embedding <=> cast(:q as vector) limit 1"
                ),
                {"q": str(query)},
            ).scalar_one()
        assert nearest == "model-placement"
    finally:
        engine.dispose()
