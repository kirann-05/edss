"""Published reports: versions, the current pointer, diff and rollback (FR-9, FR-14)."""


def publish(pipeline, edit_title=None):
    """Run, draft and approve, optionally changing the first option's title on the way."""
    reviewer, approver = pipeline.login("registrar"), pipeline.login("principal")
    _, brief_id = pipeline.draft(reviewer)
    if edit_title:
        option = approver.get(f"/api/briefs/{brief_id}").json()["document"]["option_sets"][0][
            "options"
        ][0]
        body = {
            "kind": "edit",
            "edits": [{"option_id": option["id"], "field": "title", "value": edit_title}],
        }
    else:
        body = {"kind": "approve"}
    return approver.post(f"/api/briefs/{brief_id}/decision", json=body).json()["version"]


class TestReading:
    def test_there_is_no_current_report_until_one_is_published(self, pipeline):
        assert pipeline.login("registrar").get("/api/reports/current").json() == {"current": None}

    def test_the_council_viewer_can_read_published_reports_but_never_drafts(self, pipeline):
        publish(pipeline)
        viewer = pipeline.login("viewer")
        assert viewer.get("/api/reports/current").json()["current"]["version"] == 1
        assert len(viewer.get("/api/reports/versions").json()) == 1
        assert viewer.get("/api/reports/versions/1").status_code == 200
        assert viewer.get("/api/briefs").status_code == 403
        assert pipeline.login("admin").get("/api/reports/current").status_code == 403

    def test_a_version_carries_the_fully_rendered_report_and_its_approver(self, pipeline):
        publish(pipeline)
        detail = pipeline.login("viewer").get("/api/reports/versions/1").json()
        assert detail["approved_by"] == "Dr. Kavita Rao" and detail["state"] == "current"
        assert detail["document"]["title"] == "Decision brief, 2025-26"
        refs = [
            seg
            for s in detail["document"]["summary"]
            for seg in s["text"]["segments"]
            if seg["t"] == "ref"
        ]
        assert refs and all(seg["display"] for seg in refs)

    def test_versions_are_listed_newest_first(self, pipeline):
        publish(pipeline)
        publish(pipeline)
        assert [
            v["version"] for v in pipeline.login("viewer").get("/api/reports/versions").json()
        ] == [2, 1]

    def test_an_unknown_version_is_a_404(self, pipeline):
        assert pipeline.login("registrar").get("/api/reports/versions/9").status_code == 404


class TestRollback:
    def test_rollback_moves_the_pointer_and_marks_the_replaced_version(self, pipeline):
        publish(pipeline)
        publish(pipeline)
        principal = pipeline.login("principal")
        done = principal.post(
            "/api/reports/rollback", json={"to_version": 1, "reason": "Version two was stale"}
        )
        assert done.status_code == 200 and done.json()["state"] == "current"
        states = {v["version"]: v["state"] for v in principal.get("/api/reports/versions").json()}
        assert states == {1: "current", 2: "rolled_back"}
        assert principal.get("/api/reports/current").json()["current"]["version"] == 1

    def test_rollback_needs_a_reason(self, pipeline):
        publish(pipeline)
        publish(pipeline)
        response = pipeline.login("principal").post(
            "/api/reports/rollback", json={"to_version": 1, "reason": ""}
        )
        assert response.status_code == 409

    def test_only_an_approver_can_roll_back(self, pipeline):
        publish(pipeline)
        publish(pipeline)
        for persona in ("dean", "hod_cse", "viewer"):
            response = pipeline.login(persona).post(
                "/api/reports/rollback", json={"to_version": 1, "reason": "x"}
            )
            assert response.status_code == 403, persona
        assert (
            pipeline.login("principal").get("/api/reports/current").json()["current"]["version"]
            == 2
        )

    def test_rolling_back_to_a_version_that_does_not_exist_is_refused(self, pipeline):
        publish(pipeline)
        response = pipeline.login("principal").post(
            "/api/reports/rollback", json={"to_version": 7, "reason": "x"}
        )
        assert response.status_code == 409

    def test_a_new_publication_after_a_rollback_continues_the_numbering(self, pipeline):
        publish(pipeline)
        publish(pipeline)
        pipeline.login("principal").post(
            "/api/reports/rollback", json={"to_version": 1, "reason": "back"}
        )
        assert publish(pipeline) == 3


class TestDiff:
    def test_a_diff_lists_what_an_approvers_edit_changed(self, pipeline):
        publish(pipeline)
        publish(pipeline, edit_title="A different title")
        body = pipeline.login("viewer").get("/api/reports/diff?from_version=1&to_version=2").json()
        (change,) = body["changes"]
        assert (change["section"], change["kind"], change["field"]) == (
            "options",
            "changed",
            "title",
        )
        assert change["after"] == "A different title"

    def test_identical_versions_have_no_changes(self, pipeline):
        publish(pipeline)
        publish(pipeline)
        assert (
            pipeline.login("viewer")
            .get("/api/reports/diff?from_version=1&to_version=2")
            .json()["changes"]
            == []
        )

    def test_a_diff_needs_two_real_versions(self, pipeline):
        publish(pipeline)
        client = pipeline.login("viewer")
        assert client.get("/api/reports/diff?from_version=1&to_version=5").status_code == 404
        assert client.get("/api/reports/diff?from_version=1").status_code == 422
