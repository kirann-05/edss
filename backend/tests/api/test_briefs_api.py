"""Draft briefs and the human gate over HTTP (FR-5, FR-8, FR-9)."""

from app.agents.models import CheckResult, Locator, ValidationReport, Violation


def failing_report(*ids):
    checks = []
    for n in range(1, 10):
        cid = f"V{n}"
        bad = cid in ids
        violations = (
            (
                Violation(
                    locator=Locator(section="x"),
                    message=f"{cid} failed",
                    diagnosis=f"{cid} diagnosis",
                ),
            )
            if bad
            else ()
        )
        checks.append(CheckResult(id=cid, name=cid, passed=not bad, violations=violations))
    return ValidationReport(passed=not ids, checks=tuple(checks), attempt=3)


class TestReading:
    def test_the_queue_lists_drafts_with_their_validation_state(self, pipeline):
        client = pipeline.login("registrar")
        pipeline.draft(client)
        (item,) = client.get("/api/briefs").json()
        assert item["status"] == "draft" and item["validation_passed"] is True
        assert item["escalated"] is False and item["off_target_count"] == 3
        assert item["request"] and item["period_year"] == "2025-26"

    def test_only_reviewers_see_drafts(self, pipeline):
        pipeline.draft(pipeline.login("registrar"))
        for persona in ("dean", "hod_cse", "viewer", "admin"):
            assert pipeline.login(persona).get("/api/briefs").status_code == 403, persona

    def test_a_brief_reaches_the_ui_with_every_figure_already_resolved(self, pipeline):
        client = pipeline.login("registrar")
        _, brief_id = pipeline.draft(client)
        brief = client.get(f"/api/briefs/{brief_id}").json()
        headline = next(s for s in brief["document"]["summary"] if s["kpi_key"] == "PL_PCT")
        refs = [seg for seg in headline["text"]["segments"] if seg["t"] == "ref"]
        assert [(r["field"], r["display"]) for r in refs] == [
            ("value", "75.0%"),
            ("target", "75.0%"),
            ("status", "Missed"),
            ("gap", "0.04 pts below target"),
        ]
        assert all(
            r["kind"] == "kpi" and r["key"] == "PL_PCT" and r["status"] == "missed" for r in refs
        )

    def test_the_raw_text_is_sent_too_so_an_editor_can_change_it(self, pipeline):
        client = pipeline.login("registrar")
        _, brief_id = pipeline.draft(client)
        option = client.get(f"/api/briefs/{brief_id}").json()["document"]["option_sets"][0][
            "options"
        ][0]
        assert "{{kpi:" in option["description"]["text"]
        assert any(seg["t"] == "ref" for seg in option["description"]["segments"])

    def test_every_off_target_kpi_has_options_with_risks_and_trade_offs(self, pipeline):
        client = pipeline.login("registrar")
        _, brief_id = pipeline.draft(client)
        sets = client.get(f"/api/briefs/{brief_id}").json()["document"]["option_sets"]
        assert {s["kpi_key"] for s in sets} == {"PL_PCT", "RS_PUB_PF", "AC_PASS_PCT"}
        for option_set in sets:
            assert 2 <= len(option_set["options"]) <= 3
            for option in option_set["options"]:
                assert option["assumptions"] and option["risks"] and option["trade_offs"]

    def test_the_brief_says_what_it_rests_on(self, pipeline):
        client = pipeline.login("registrar")
        _, brief_id = pipeline.draft(client)
        kinds = {
            a["kind"]
            for a in client.get(f"/api/briefs/{brief_id}").json()["document"]["assumptions"]
        }
        assert {"as_of", "placeholder", "stale", "missing", "excluded", "undefined"} <= kinds

    def test_evidence_lists_the_records_and_systems_behind_each_kpi(self, pipeline):
        client = pipeline.login("registrar")
        _, brief_id = pipeline.draft(client)
        rows = {r["kpi_key"]: r for r in client.get(f"/api/briefs/{brief_id}/evidence").json()}
        assert len(rows) == 13
        placement = rows["PL_PCT"]
        assert placement["fact_ids"] and placement["source_systems"] == [
            "Placement Cell offers view"
        ]
        assert "8 departments" in placement["scope"] and "placeholder" in placement["tags"]

    def test_prior_briefs_come_back_ranked_with_what_leadership_did(self, pipeline):
        client = pipeline.login("registrar")
        _, brief_id = pipeline.draft(client)
        matches = client.get(f"/api/briefs/{brief_id}/prior").json()
        assert matches and matches[0]["score"] > 0
        assert all(m["decision"] and m["matching_kpis"] and m["reason"] for m in matches)
        assert [m["score"] for m in matches] == sorted((m["score"] for m in matches), reverse=True)

    def test_an_unknown_brief_is_a_404(self, pipeline):
        client = pipeline.login("registrar")
        assert client.get("/api/briefs/brief-99").status_code == 404
        assert client.get("/api/briefs/brief-99/evidence").status_code == 404


class TestApprove:
    def test_a_principal_approves_and_version_one_is_published(self, pipeline):
        client = pipeline.login("principal")
        run_id, brief_id = pipeline.draft(pipeline.login("registrar"))
        body = client.post(f"/api/briefs/{brief_id}/decision", json={"kind": "approve"}).json()
        assert body["brief"]["status"] == "published" and body["version"] == 1
        assert body["brief"]["approval"]["actor_name"] == "Dr. Kavita Rao"
        assert client.get("/api/reports/current").json()["current"]["version"] == 1
        assert (
            client.get(f"/api/runs/{run_id}").json()["status"] == "completed"
        )  # the graph finished

    def test_a_dean_cannot_approve_and_the_refusal_is_logged(self, pipeline):
        _, brief_id = pipeline.draft(pipeline.login("registrar"))
        response = pipeline.login("dean").post(
            f"/api/briefs/{brief_id}/decision", json={"kind": "approve"}
        )
        assert response.status_code == 403
        assert pipeline.state.governance.current() is None
        assert pipeline.state.audit.rows(action="brief.refused")

    def test_a_brief_can_only_be_decided_once(self, pipeline):
        client = pipeline.login("principal")
        _, brief_id = pipeline.draft(pipeline.login("registrar"))
        client.post(f"/api/briefs/{brief_id}/decision", json={"kind": "approve"})
        again = client.post(f"/api/briefs/{brief_id}/decision", json={"kind": "approve"})
        assert again.status_code == 409 and "already" in again.json()["detail"]

    def test_the_server_says_whether_approve_is_allowed(self, pipeline):
        client = pipeline.login("registrar")
        _, brief_id = pipeline.draft(client)
        state = client.get(f"/api/briefs/{brief_id}").json()["approval_state"]
        assert state == {
            "can_approve": True,
            "blocked_reason": None,
            "needs_acknowledgement": False,
            "failing_checks": [],
        }

    def test_whether_a_role_can_decide_is_reported_for_the_ui(self, pipeline):
        _, brief_id = pipeline.draft(pipeline.login("registrar"))
        assert (
            pipeline.login("principal").get(f"/api/briefs/{brief_id}").json()["can_decide"] is True
        )


class TestEscalated:
    def make(self, pipeline, *failing):
        draft = pipeline.state.governance.create_draft(
            run_id="run-x",
            document=pipeline.state.governance.briefs()[0].document
            if pipeline.state.governance.briefs()
            else None,
            validation=failing_report(*failing),
            attempts=3,
            escalated=True,
            diagnosis="needs a person",
            repair_log=(),
            created_by="registrar@edss.test",
        )
        return draft.id

    def seed(self, pipeline):
        pipeline.draft(pipeline.login("registrar"))  # gives us a real document to reuse

    def test_an_integrity_failure_blocks_approval_and_the_ui_is_told_why(self, pipeline):
        self.seed(pipeline)
        brief_id = self.make(pipeline, "V1")
        client = pipeline.login("principal")
        state = client.get(f"/api/briefs/{brief_id}").json()["approval_state"]
        assert state["can_approve"] is False and "V1" in state["blocked_reason"]
        response = client.post(
            f"/api/briefs/{brief_id}/decision", json={"kind": "approve", "ack_escalation": True}
        )
        assert response.status_code == 409 and "integrity" in response.json()["detail"]

    def test_a_completeness_failure_needs_an_acknowledgement(self, pipeline):
        self.seed(pipeline)
        brief_id = self.make(pipeline, "V3")
        client = pipeline.login("principal")
        assert (
            client.get(f"/api/briefs/{brief_id}").json()["approval_state"]["needs_acknowledgement"]
            is True
        )
        assert (
            client.post(f"/api/briefs/{brief_id}/decision", json={"kind": "approve"}).status_code
            == 409
        )
        ok = client.post(
            f"/api/briefs/{brief_id}/decision", json={"kind": "approve", "ack_escalation": True}
        )
        assert ok.status_code == 200 and ok.json()["brief"]["approval"]["ack_escalation"] is True


class TestEdit:
    def edit(self, brief, value, field="description"):
        option = brief["document"]["option_sets"][0]["options"][0]
        return {"option_id": option["id"], "field": field, "value": value}

    def test_a_valid_edit_is_published_and_shown_as_a_diff(self, pipeline):
        client = pipeline.login("principal")
        _, brief_id = pipeline.draft(pipeline.login("registrar"))
        brief = client.get(f"/api/briefs/{brief_id}").json()
        edit = self.edit(brief, "Concentrate support where the figure is weakest.")
        body = client.post(
            f"/api/briefs/{brief_id}/decision", json={"kind": "edit", "edits": [edit]}
        ).json()
        assert body["brief"]["status"] == "published"
        (recorded,) = body["brief"]["edits"]
        assert (
            recorded["after"] == "Concentrate support where the figure is weakest."
            and recorded["by"]
        )

    def test_an_edit_that_writes_a_figure_by_hand_is_refused_with_the_report(self, pipeline):
        client = pipeline.login("principal")
        _, brief_id = pipeline.draft(pipeline.login("registrar"))
        edit = self.edit(client.get(f"/api/briefs/{brief_id}").json(), "Raise it by 12%.")
        response = client.post(
            f"/api/briefs/{brief_id}/decision", json={"kind": "edit", "edits": [edit]}
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "validation" in detail["message"]
        assert any(c["id"] == "V1" and not c["passed"] for c in detail["report"]["checks"])
        assert client.get(f"/api/briefs/{brief_id}").json()["status"] == "draft"
        assert client.get("/api/reports/current").json()["current"] is None

    def test_a_dry_run_reports_what_validation_would_say_and_changes_nothing(self, pipeline):
        client = pipeline.login("principal")
        _, brief_id = pipeline.draft(pipeline.login("registrar"))
        brief = client.get(f"/api/briefs/{brief_id}").json()
        bad = client.post(
            f"/api/briefs/{brief_id}/check-edits",
            json={"edits": [self.edit(brief, "Raise it by 12%.")]},
        ).json()
        good = client.post(
            f"/api/briefs/{brief_id}/check-edits",
            json={"edits": [self.edit(brief, "A calm sentence.")]},
        ).json()
        assert not bad["report"]["passed"] and good["report"]["passed"]
        assert client.get(f"/api/briefs/{brief_id}").json()["status"] == "draft"

    def test_a_figure_can_be_added_to_an_edit_only_as_a_token(self, pipeline):
        client = pipeline.login("principal")
        _, brief_id = pipeline.draft(pipeline.login("registrar"))
        edit = self.edit(
            client.get(f"/api/briefs/{brief_id}").json(), "Placement stands at {{kpi:PL_PCT}} now."
        )
        assert client.post(f"/api/briefs/{brief_id}/check-edits", json={"edits": [edit]}).json()[
            "report"
        ]["passed"]

    def test_an_edit_to_an_option_that_does_not_exist_is_refused(self, pipeline):
        client = pipeline.login("principal")
        _, brief_id = pipeline.draft(pipeline.login("registrar"))
        response = client.post(
            f"/api/briefs/{brief_id}/check-edits",
            json={"edits": [{"option_id": "NOPE-1", "field": "description", "value": "x"}]},
        )
        assert response.status_code == 422


class TestOverrideAndSendBack:
    def test_an_override_needs_a_reason_and_publishes_nothing(self, pipeline):
        client = pipeline.login("principal")
        run_id, brief_id = pipeline.draft(pipeline.login("registrar"))
        assert (
            client.post(f"/api/briefs/{brief_id}/decision", json={"kind": "override"}).status_code
            == 409
        )
        done = client.post(
            f"/api/briefs/{brief_id}/decision", json={"kind": "override", "reason": "Postponed"}
        ).json()
        assert (
            done["brief"]["status"] == "overridden"
            and done["brief"]["decision_reason"] == "Postponed"
        )
        assert done["version"] is None
        assert client.get("/api/reports/current").json()["current"] is None
        assert client.get(f"/api/runs/{run_id}").json()["status"] == "completed"

    def test_sending_back_records_the_reason(self, pipeline):
        client = pipeline.login("principal")
        _, brief_id = pipeline.draft(pipeline.login("registrar"))
        done = client.post(
            f"/api/briefs/{brief_id}/decision",
            json={"kind": "send_back", "reason": "Redo research"},
        ).json()
        assert done["brief"]["status"] == "returned"
