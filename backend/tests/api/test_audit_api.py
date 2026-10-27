"""The audit viewer and chain verification (FR-12, rule 9)."""

from dataclasses import replace


class TestRead:
    def test_an_approver_sees_every_step_and_decision_newest_first(self, pipeline):
        client = pipeline.login("registrar")
        _, brief_id = pipeline.draft(client)
        pipeline.login("principal").post(
            f"/api/briefs/{brief_id}/decision", json={"kind": "approve"}
        )
        page = client.get("/api/audit?limit=500").json()
        actions = {r["action"] for r in page["rows"]}
        assert {
            "run.create",
            "plan.lock",
            "node.done",
            "brief.approve",
            "report.publish",
        } <= actions
        ids = [r["id"] for r in page["rows"]]
        assert ids == sorted(ids, reverse=True) and page["total"] == len(ids)

    def test_rows_carry_inputs_outputs_and_their_place_in_the_chain(self, pipeline):
        client = pipeline.login("registrar")
        pipeline.draft(client)
        row = next(
            r
            for r in client.get("/api/audit?action=node.done&limit=500").json()["rows"]
            if r["actor_id"] == "kpi_synthesis"
        )
        assert (
            row["inputs"]["digest"]
            and row["outputs"]["digest"]
            and row["outputs"]["elapsed_ms"] >= 0
        )
        assert len(row["hash"]) == 64 and len(row["prev_hash"]) == 64

    def test_a_decision_row_names_the_person_and_the_reason(self, pipeline):
        _, brief_id = pipeline.draft(pipeline.login("registrar"))
        principal = pipeline.login("principal")
        principal.post(
            f"/api/briefs/{brief_id}/decision",
            json={"kind": "override", "reason": "Council postponed"},
        )
        row = principal.get("/api/audit?action=brief.override").json()["rows"][0]
        assert row["actor_id"] == "principal@edss.test" and row["actor_type"] == "user"
        assert row["outputs"]["reason"] == "Council postponed"

    def test_filters_narrow_the_rows(self, pipeline):
        client = pipeline.login("registrar")
        first, _ = pipeline.draft(client)
        second, _ = pipeline.draft(client)
        only_first = client.get(f"/api/audit?run_id={first}&limit=500").json()
        assert only_first["rows"] and {r["run_id"] for r in only_first["rows"]} == {first}
        assert client.get(f"/api/audit?run_id={second}&action=plan.lock").json()["total"] == 1
        assert client.get("/api/audit?actor=domain:finance&limit=500").json()["total"] == 2

    def test_people_only_shows_what_people_did(self, pipeline):
        client = pipeline.login("registrar")
        pipeline.draft(client)
        everything = client.get("/api/audit?limit=500").json()
        people = client.get("/api/audit?actor_type=user&limit=500").json()
        assert 0 < people["total"] < everything["total"]
        assert {r["actor_type"] for r in people["rows"]} == {"user"}
        assert {"run.create", "plan.lock"} <= {r["action"] for r in people["rows"]}

    def test_paging_walks_the_whole_log(self, pipeline):
        client = pipeline.login("registrar")
        pipeline.draft(client)
        total = client.get("/api/audit?limit=1").json()["total"]
        seen = []
        for offset in range(0, total, 7):
            seen += [
                r["id"] for r in client.get(f"/api/audit?limit=7&offset={offset}").json()["rows"]
            ]
        assert len(seen) == total == len(set(seen))

    def test_only_roles_with_audit_access_may_read_it(self, pipeline):
        for persona in ("dean", "hod_cse", "viewer", "admin"):
            client = pipeline.login(persona)
            assert client.get("/api/audit").status_code == 403, persona
            assert client.get("/api/audit/verify").status_code == 403, persona
        assert pipeline.login("principal").get("/api/audit").status_code == 200


class TestVerify:
    def test_an_untouched_log_verifies(self, pipeline):
        client = pipeline.login("registrar")
        pipeline.draft(client, faults=["fake_number"])
        body = client.get("/api/audit/verify").json()
        assert body["ok"] is True and body["checked"] >= 19 and body["broken_at"] is None

    def test_tampering_is_detected_at_the_row_that_was_changed(self, pipeline):
        client = pipeline.login("registrar")
        pipeline.draft(client)
        rows = (
            pipeline.state.audit._rows
        )  # reaching in is the point: this is what an attacker would do
        target = len(rows) // 2
        rows[target] = replace(rows[target], outputs={"summary": "rewritten after the fact"})
        body = client.get("/api/audit/verify").json()
        assert body["ok"] is False and body["broken_at"] == rows[target].id
        assert "no longer matches" in body["reason"]


def test_the_action_filter_offers_only_actions_that_exist(pipeline):
    client = pipeline.login("registrar")
    pipeline.start(client)
    actions = client.get("/api/audit/actions").json()
    assert actions == sorted(set(actions))
    assert {"auth.login", "plan.lock", "node.done", "gate.waiting"} <= set(actions)


def test_listing_actions_needs_audit_access(pipeline):
    assert pipeline.login("dean").get("/api/audit/actions").status_code == 403


def test_a_time_filter_without_a_zone_is_read_as_utc(pipeline):
    client = pipeline.login("registrar")
    everything = client.get("/api/audit?since=2000-01-01T00:00:00").json()
    assert everything["total"] > 0
    nothing = client.get("/api/audit?until=2000-01-01T00:00:00").json()
    assert nothing["total"] == 0
