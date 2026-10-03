"""Runs over HTTP: clarify, plan, revise, lock, watch (FR-1, FR-12, FR-13)."""

import json

VAGUE = "Prepare the leadership brief"
SPECIFIC = "Governing Council brief for 2025-26 on everything"


class TestClarify:
    def test_a_vague_request_gets_clarifying_questions_with_their_reasons(self, pipeline):
        client = pipeline.login("registrar")
        run = client.post("/api/runs", json={"request": VAGUE}).json()
        assert run["status"] == "clarifying" and run["plan"] is None
        assert len(run["questions"]) >= 2
        assert all(q["why"] and q["text"] for q in run["questions"])
        period = next(q for q in run["questions"] if q["id"] == "period")
        assert period["choices"][0] == "2025-26"

    def test_a_specific_request_goes_straight_to_a_plan(self, pipeline):
        run = pipeline.login("registrar").post("/api/runs", json={"request": SPECIFIC}).json()
        assert run["status"] == "planning" and run["questions"] == []
        assert run["plan"]["period_year"] == "2025-26" and len(run["plan"]["kpi_keys"]) == 13

    def test_answering_the_questions_produces_a_plan_that_follows_them(self, pipeline):
        client = pipeline.login("registrar")
        run = client.post("/api/runs", json={"request": VAGUE}).json()
        answers = [
            {"question_id": "period", "answer": "2024-25"},
            {"question_id": "scope", "answer": "Placement and Finance"},
            {"question_id": "audience", "answer": "Governing Council review"},
        ]
        done = client.post(f"/api/runs/{run['id']}/answers", json={"answers": answers}).json()
        assert done["status"] == "planning"
        assert done["plan"]["period_year"] == "2024-25"
        assert set(done["plan"]["domains"]) == {"placement", "finance"}

    def test_an_answer_is_returned_with_the_words_of_its_question(self, pipeline):
        client = pipeline.login("registrar")
        run = client.post("/api/runs", json={"request": VAGUE}).json()
        asked = {q["id"]: q["text"] for q in run["questions"]}
        after = client.post(
            f"/api/runs/{run['id']}/answers",
            json={"answers": [{"question_id": "period", "answer": "2024-25"}]},
        ).json()
        assert after["answers"] == [
            {"question_id": "period", "question": asked["period"], "answer": "2024-25"}
        ]

    def test_a_partial_answer_leaves_only_the_remaining_questions(self, pipeline):
        client = pipeline.login("registrar")
        run = client.post("/api/runs", json={"request": VAGUE}).json()
        after = client.post(
            f"/api/runs/{run['id']}/answers",
            json={"answers": [{"question_id": "period", "answer": "2025-26"}]},
        ).json()
        assert after["status"] == "clarifying"
        assert {q["id"] for q in after["questions"]} == {"scope", "audience"}

    def test_a_person_can_skip_the_questions_and_get_plain_defaults(self, pipeline):
        client = pipeline.login("registrar")
        run = client.post("/api/runs", json={"request": VAGUE}).json()
        plan = client.post(f"/api/runs/{run['id']}/skip-questions").json()["plan"]
        assert plan["period_year"] == "2025-26" and len(plan["domains"]) == 4

    def test_answering_a_question_that_was_not_asked_is_refused(self, pipeline):
        client = pipeline.login("registrar")
        run = client.post("/api/runs", json={"request": VAGUE}).json()
        response = client.post(
            f"/api/runs/{run['id']}/answers",
            json={"answers": [{"question_id": "mood", "answer": "x"}]},
        )
        assert response.status_code == 409

    def test_an_empty_request_is_refused(self, pipeline):
        assert (
            pipeline.login("registrar").post("/api/runs", json={"request": "  "}).status_code == 409
        )


class TestPlan:
    def make(self, pipeline):
        client = pipeline.login("registrar")
        return client, client.post("/api/runs", json={"request": SPECIFIC}).json()

    def test_feedback_revises_the_plan_and_says_what_changed(self, pipeline):
        client, run = self.make(pipeline)
        body = client.post(
            f"/api/runs/{run['id']}/plan/revise", json={"feedback": "Drop finance please"}
        ).json()
        assert "finance" not in body["run"]["plan"]["domains"]
        assert any("Finance" in c for c in body["changes"])
        assert body["run"]["plan"]["revision"] == 2
        assert [h["revision"] for h in body["run"]["plan_history"]] == [1, 2]

    def test_a_person_can_edit_the_plan_directly(self, pipeline):
        client, run = self.make(pipeline)
        plan = client.put(
            f"/api/runs/{run['id']}/plan",
            json={"period_year": "2024-25", "kpi_keys": ["PL_PCT", "AC_CO"]},
        ).json()["plan"]
        assert plan["period_year"] == "2024-25" and plan["kpi_keys"] == ["PL_PCT", "AC_CO"]

    def test_a_nonsense_edit_is_refused_with_the_reason(self, pipeline):
        client, run = self.make(pipeline)
        response = client.put(f"/api/runs/{run['id']}/plan", json={"period_year": "1999-00"})
        assert response.status_code == 409 and "period" in response.json()["detail"]

    def test_empty_feedback_is_refused(self, pipeline):
        client, run = self.make(pipeline)
        assert (
            client.post(f"/api/runs/{run['id']}/plan/revise", json={"feedback": " "}).status_code
            == 409
        )


class TestLockAndRun:
    def test_locking_runs_the_graph_to_the_human_gate(self, pipeline):
        client = pipeline.login("registrar")
        run = pipeline.start(client)
        assert run["status"] == "awaiting_review"
        assert run["plan"]["locked_at"] is not None
        assert run["brief_id"] and run["error"] is None

    def test_a_locked_plan_cannot_be_edited_revised_or_locked_again(self, pipeline):
        client = pipeline.login("registrar")
        run = pipeline.start(client)
        assert (
            client.put(f"/api/runs/{run['id']}/plan", json={"period_year": "2024-25"}).status_code
            == 409
        )
        assert (
            client.post(
                f"/api/runs/{run['id']}/plan/revise", json={"feedback": "Drop finance"}
            ).status_code
            == 409
        )
        assert client.post(f"/api/runs/{run['id']}/plan/lock", json={}).status_code == 409

    def test_failure_injection_is_detected_and_repaired_and_the_attempts_are_visible(
        self, pipeline
    ):
        client = pipeline.login("registrar")
        _, brief_id = pipeline.draft(client, faults=["fake_number"])
        brief = client.get(f"/api/briefs/{brief_id}").json()
        assert brief["attempts"] == 2 and brief["escalated"] is False
        first, last = brief["history"][0], brief["history"][-1]
        assert not first["passed"] and last["passed"]
        assert [c["id"] for c in first["checks"] if not c["passed"]] == ["V1"]
        assert brief["repair_log"] and brief["repair_log"][0].startswith("Regenerated options")

    def test_an_unknown_fault_is_refused(self, pipeline):
        client = pipeline.login("registrar")
        run = client.post("/api/runs", json={"request": SPECIFIC}).json()
        assert (
            client.post(
                f"/api/runs/{run['id']}/plan/lock", json={"faults": ["gremlins"]}
            ).status_code
            == 409
        )

    def test_failure_injection_is_refused_unless_the_data_is_synthetic(self, pipeline):
        pipeline.state.system_config.set_data_mode("real")
        client = pipeline.login("registrar")
        run = client.post("/api/runs", json={"request": SPECIFIC}).json()
        response = client.post(f"/api/runs/{run['id']}/plan/lock", json={"faults": ["fake_number"]})
        assert response.status_code == 409 and "synthetic" in response.json()["detail"]

    def test_a_run_that_cannot_get_access_stops_with_a_reason_and_can_be_resumed(self, pipeline):
        from datetime import date

        from app.domain.enums import Domain

        pipeline.state.scopes.revoke(Domain.FINANCE)
        client = pipeline.login("registrar")
        run = pipeline.start(client)
        assert run["status"] == "failed" and "Finance" in run["error"]

        pipeline.state.scopes.grant(Domain.FINANCE, "registrar@edss.test", date(2026, 10, 1))
        resumed = client.post(f"/api/runs/{run['id']}/resume").json()
        assert resumed["status"] == "awaiting_review" and resumed["error"] is None

    def test_a_run_that_is_not_failed_cannot_be_resumed(self, pipeline):
        client = pipeline.login("registrar")
        run = pipeline.start(client)
        assert client.post(f"/api/runs/{run['id']}/resume").status_code == 409


class TestWhoMaySee:
    def test_only_people_who_may_start_a_run_can_start_one(self, pipeline):
        for persona in ("hod_cse", "viewer", "admin"):
            assert (
                pipeline.login(persona).post("/api/runs", json={"request": SPECIFIC}).status_code
                == 403
            ), persona
        assert (
            pipeline.login("dean").post("/api/runs", json={"request": SPECIFIC}).status_code == 201
        )

    def test_a_run_is_visible_to_its_owner_and_to_reviewers_but_not_to_others(self, pipeline):
        dean = pipeline.login("dean")
        run = dean.post("/api/runs", json={"request": SPECIFIC}).json()
        assert pipeline.login("registrar").get(f"/api/runs/{run['id']}").status_code == 200
        registrar_run = (
            pipeline.login("registrar").post("/api/runs", json={"request": SPECIFIC}).json()
        )
        assert (
            dean.get(f"/api/runs/{registrar_run['id']}").status_code == 404
        )  # not even its existence

    def test_the_list_shows_a_person_their_own_runs(self, pipeline):
        dean = pipeline.login("dean")
        mine = dean.post("/api/runs", json={"request": SPECIFIC}).json()
        pipeline.login("registrar").post("/api/runs", json={"request": SPECIFIC})
        assert [r["id"] for r in dean.get("/api/runs").json()] == [mine["id"]]
        assert len(pipeline.login("principal").get("/api/runs").json()) == 2

    def test_an_unknown_run_is_a_404(self, pipeline):
        assert pipeline.login("registrar").get("/api/runs/run-999").status_code == 404


class TestCatalogue:
    def test_it_lists_what_a_plan_may_choose_from(self, pipeline):
        body = pipeline.login("registrar").get("/api/plan-catalogue").json()
        assert body["periods"] == ["2023-24", "2024-25", "2025-26"]
        assert len(body["kpis"]) == 13 and len(body["domains"]) == 4
        assert len(body["audiences"]) == 2

    def test_failure_injection_options_are_offered_only_for_synthetic_data(self, pipeline):
        client = pipeline.login("registrar")
        assert len(client.get("/api/plan-catalogue").json()["faults"]) == 8
        pipeline.state.system_config.set_data_mode("real")
        assert client.get("/api/plan-catalogue").json()["faults"] == []


class TestProgressStream:
    def read(self, client, url, **kw):
        events, end = [], None
        with client.stream("GET", url, **kw) as response:
            assert response.headers["content-type"].startswith("text/event-stream")
            kind = None
            for line in response.iter_lines():
                if line.startswith("event: "):
                    kind = line[7:]
                elif line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if kind == "end":
                        end = payload
                    else:
                        events.append(payload)
        return events, end

    def test_the_stream_asks_proxies_not_to_compress_or_buffer_it(self, pipeline):
        client = pipeline.login("registrar")
        run = pipeline.start(client)
        with client.stream("GET", f"/api/runs/{run['id']}/events") as response:
            control = response.headers["cache-control"]
            assert "no-transform" in control and "no-cache" in control
            assert response.headers["x-accel-buffering"] == "no"

    def test_a_finished_run_replays_its_progress_and_says_when_it_ends(self, pipeline):
        client = pipeline.login("registrar")
        run = pipeline.start(client)
        events, end = self.read(client, f"/api/runs/{run['id']}/events")
        nodes = {e["node"] for e in events}
        assert {"plan_lock", "access_check", "kpi_synthesis", "report_compose", "validate"} <= nodes
        assert {"domain:academic", "domain:finance", "options:PL_PCT"} <= nodes
        assert events[-1]["state"] == "waiting" and events[-1]["node"] == "human_gate"
        assert end == {"status": "awaiting_review"}

    def test_events_carry_timings_and_attempts_for_the_ui(self, pipeline):
        client = pipeline.login("registrar")
        run = pipeline.start(client, faults=["fake_number"])
        events, _ = self.read(client, f"/api/runs/{run['id']}/events")
        validations = [e for e in events if e["node"] == "validate" and e["state"] == "done"]
        assert [v["ok"] for v in validations] == [False, True]
        assert (
            validations[0]["detail"] == "Failing: V1 Every figure cites its source"
            and validations[1]["detail"] == "All nine checks passed"
        )
        done = [e for e in events if e["state"] == "done" and e["node"].startswith("domain:")]
        assert all(e["elapsed_ms"] is not None for e in done)

    def test_a_reconnect_resumes_after_the_last_event_it_saw(self, pipeline):
        client = pipeline.login("registrar")
        run = pipeline.start(client)
        everything, _ = self.read(client, f"/api/runs/{run['id']}/events")
        cut = everything[3]["id"]
        rest, _ = self.read(
            client, f"/api/runs/{run['id']}/events", headers={"Last-Event-ID": str(cut)}
        )
        assert [e["id"] for e in rest] == [e["id"] for e in everything if e["id"] > cut]
        also, _ = self.read(client, f"/api/runs/{run['id']}/events?after={cut}")
        assert also == rest

    def test_someone_else_cannot_watch_a_run(self, pipeline):
        run = pipeline.start(pipeline.login("registrar"))
        assert pipeline.login("dean").get(f"/api/runs/{run['id']}/events").status_code == 404


class TestTrace:
    def test_a_reviewer_with_audit_access_gets_the_events_and_the_audit_rows(self, pipeline):
        client = pipeline.login("registrar")
        run = pipeline.start(client)
        body = client.get(f"/api/runs/{run['id']}/trace").json()
        assert body["events"] and body["audit"]
        actions = {r["action"] for r in body["audit"]}
        assert {"run.create", "plan.lock", "node.done", "gate.waiting"} <= actions

    def test_without_audit_access_there_is_no_trace(self, pipeline):
        run = pipeline.start(pipeline.login("registrar"))
        assert pipeline.login("dean").get(f"/api/runs/{run['id']}/trace").status_code == 403
