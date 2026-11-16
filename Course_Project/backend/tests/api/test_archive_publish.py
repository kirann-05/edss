"""A published report becomes a prior for the briefs after it (Lab 4 memory, filling the archive)."""

from fastapi.testclient import TestClient

from app.governance.service import Decision
from app.main import create_app
from app.services.demo_state import DRAFT_REQUEST, REPORT_REQUEST, _draft
from tests.api.conftest import REF, make_settings


def started():
    app = create_app(make_settings(edss_demo_login=True), today=REF)
    client = TestClient(app)
    client.post("/api/auth/demo-login", json={"email": "principal@edss.test"})
    return app, client


def test_a_published_report_is_offered_as_a_prior_to_the_next_brief_but_not_to_itself():
    app, client = started()
    state = app.state.edss
    principal = state.users.by_email("principal@edss.test")
    published = _draft(state, REPORT_REQUEST)
    version = state.governance.decide(
        published.brief_id, principal, Decision(kind="approve")
    ).version
    waiting = _draft(state, DRAFT_REQUEST)

    priors = client.get(f"/api/briefs/{waiting.brief_id}/prior").json()
    ours = [p for p in priors if p["id"] == f"report-v{version.version}"]
    assert ours and ours[0]["decision"].startswith(
        f"Approved by {principal.name} as version {version.version}"
    )
    assert f"report-v{version.version}" not in [
        p["id"] for p in client.get(f"/api/briefs/{published.brief_id}/prior").json()
    ]


def test_if_the_archive_fails_the_approval_still_stands_and_the_failure_is_audited():
    app, _ = started()
    state = app.state.edss

    def broken(prior):
        raise RuntimeError("the embedding model is not answering")

    state.archive.add = broken
    principal = state.users.by_email("principal@edss.test")
    draft = _draft(state, REPORT_REQUEST)
    result = state.governance.decide(draft.brief_id, principal, Decision(kind="approve"))
    assert result.version is not None and result.brief.status.value == "published"
    assert [
        r
        for r in state.audit.rows(action="archive.add_failed")
        if "not answering" in r.outputs["error"]
    ]
