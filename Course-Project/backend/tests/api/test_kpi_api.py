import re

PLAIN_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")


def kpis_by_key(client, period=None):
    url = "/api/kpis" + (f"?period={period}" if period else "")
    body = client.get(url).json()
    return body, {k["key"]: k for k in body["kpis"]}


def test_the_dashboard_list_has_every_kpi_with_the_design_outcome(login):
    body, kpis = kpis_by_key(login("registrar"))
    assert body["period_year"] == "2025-26"
    assert body["is_current"] is True
    assert len(kpis) == 13
    assert body["summary"] == {"met": 10, "at_risk": 1, "missed": 2, "undefined": 0}


def test_t6_a_miss_arrives_exact_and_marked_missed(login):
    _, kpis = kpis_by_key(login("registrar"))
    placement = kpis["PL_PCT"]
    assert placement["value"] == "74.96"
    assert placement["target"] == "75"
    assert placement["variance_abs"] == "-0.04"
    assert placement["status"] == "missed"
    assert placement["precision"] == 1  # the UI rounds to this, and must not hide the miss


def test_every_figure_is_a_plain_decimal_string_never_a_float_or_exponent(login):
    _, kpis = kpis_by_key(login("registrar"))
    for kpi in kpis.values():
        for field in ("value", "target", "variance_abs", "variance_pct"):
            if kpi[field] is not None:
                assert isinstance(kpi[field], str), (kpi["key"], field)
                assert PLAIN_DECIMAL.match(kpi[field]), (kpi["key"], field, kpi[field])


def test_placeholder_kpis_say_so_and_claim_no_official_framework(login):
    _, kpis = kpis_by_key(login("registrar"))
    for kpi in kpis.values():
        assert kpi["placeholder"] is True
        assert kpi["framework"] == "STRATEGIC"
        assert "PLACEHOLDER_PENDING_IQAC" in kpi["note"]


def test_each_kpi_carries_a_three_period_trend_oldest_first(login):
    _, kpis = kpis_by_key(login("registrar"))
    for kpi in kpis.values():
        assert [t["period_year"] for t in kpi["trend"]] == ["2023-24", "2024-25", "2025-26"]
    assert kpis["PL_PCT"]["trend"][-1]["value"] == "74.96"


def test_flags_say_which_departments_are_stale_missing_excluded_or_undefined(login):
    _, kpis = kpis_by_key(login("registrar"))
    assert kpis["PL_PCT"]["flags"]["stale"] == {"departments": ["CIVIL"], "total": 1}
    assert kpis["PL_PCT"]["flags"]["undefined"] == {"departments": ["AIML"], "total": 1}
    assert kpis["RS_PUB_PF"]["flags"]["missing"] == {"departments": ["MECH"], "total": 1}
    assert kpis["FN_UTIL"]["flags"]["excluded"] == {"departments": ["BIOTECH"], "total": 1}
    assert kpis["FN_UTIL"]["flags"]["excluded_fact_count"] == 1


def test_an_earlier_period_can_be_asked_for_and_is_not_judged_stale(login):
    body, kpis = kpis_by_key(login("registrar"), "2024-25")
    assert body["period_year"] == "2024-25"
    assert body["is_current"] is False
    assert kpis["PL_PCT"]["flags"]["stale"]["total"] == 0
    assert kpis["PL_PCT"]["period_year"] == "2024-25"


def test_an_unknown_period_is_a_404(login):
    assert login("registrar").get("/api/kpis?period=1999-00").status_code == 404


class TestDrilldown:
    def test_it_shows_the_formula_inputs_departments_spread_and_source_facts(self, login):
        response = login("registrar").get("/api/kpis/PL_PCT")
        assert response.status_code == 200
        body = response.json()
        assert body["access"] == "full"
        assert (
            body["kpi"]["formula_text"]
            == "100 × total placed, verified by Placement Cell ÷ total students registered"
        )
        assert {i["label"]: i["value"] for i in body["inputs"]} == {
            "sum(plc.placed_confirmed)": "937",
            "sum(plc.registered)": "1250",
        }
        assert len(body["departments"]) == 8
        fact = body["facts"][0]
        assert fact["source_system"] and fact["source_ref"] and fact["as_of"]
        assert fact["status"] in {"final", "audited"}
        assert fact["used"] is True

    def test_departments_carry_their_own_state_value_and_inputs(self, login):
        rows = {
            r["dept_code"]: r
            for r in login("registrar").get("/api/kpis/PL_PCT").json()["departments"]
        }
        assert rows["AIML"]["state"] == "undefined"
        assert rows["AIML"]["value"] is None  # zero denominator, not 0 and not 100
        assert rows["CIVIL"]["stale"] is True
        assert rows["CSE"]["state"] == "ok"
        assert {i["label"] for i in rows["CSE"]["inputs"]} == {
            "sum(plc.placed_confirmed)",
            "sum(plc.registered)",
        }

    def test_t7_the_spread_shows_the_simple_mean_beside_the_weighted_value(self, login):
        body = login("registrar").get("/api/kpis/AC_PASS_PCT").json()
        spread = body["spread"]
        assert float(spread["simple_mean"]) - float(body["kpi"]["value"]) > 2
        assert float(spread["min"]) < float(spread["median"]) < float(spread["max"])
        assert spread["count"] == 8

    def test_t8_an_unreconciled_figure_is_listed_with_its_badge_and_marked_unused(self, login):
        body = login("registrar").get("/api/kpis/FN_UTIL").json()
        rows = {r["dept_code"]: r for r in body["departments"]}
        assert rows["BIOTECH"]["state"] == "excluded"
        assert "not final or audited" in rows["BIOTECH"]["reason"]
        unused = [f for f in body["facts"] if not f["used"]]
        assert [(f["dept_code"], f["status"]) for f in unused] == [
            ("BIOTECH", "pending_reconciliation")
        ]

    def test_t2_a_missing_department_says_why_instead_of_showing_zero(self, login):
        rows = {
            r["dept_code"]: r
            for r in login("registrar").get("/api/kpis/RS_PUB_PF").json()["departments"]
        }
        assert rows["MECH"]["state"] == "missing"
        assert rows["MECH"]["value"] is None
        assert "res.publications_count" in rows["MECH"]["reason"]

    def test_an_unknown_kpi_is_a_404(self, login):
        assert login("registrar").get("/api/kpis/NOPE").status_code == 404


class TestDomainView:
    def test_each_domain_lists_its_kpis_with_every_department(self, login):
        client = login("registrar")
        counts = {d: len(client.get(f"/api/domains/{d}").json()["kpis"])
                  for d in ("academic", "research", "placement", "finance")}  # fmt: skip
        assert counts == {"academic": 4, "research": 3, "placement": 3, "finance": 3}
        body = client.get("/api/domains/placement").json()
        assert all(len(k["departments"]) == 8 for k in body["kpis"])

    def test_the_reference_domain_is_not_a_tab(self, login):
        assert login("registrar").get("/api/domains/reference").status_code == 404

    def test_an_unknown_domain_is_rejected(self, login):
        assert login("registrar").get("/api/domains/astrology").status_code == 422


def test_system_status_says_plainly_when_drafts_are_canned(login):
    body = login("registrar").get("/api/system/status").json()
    assert body["data_mode"] == "synthetic"
    assert body["llm_provider"] == "fake"
    assert body["llm_is_fake"] is True
    assert body["current_period"] == "2025-26"
    assert body["periods"] == ["2023-24", "2024-25", "2025-26"]
    # the pause that stands in for a slow source is stated, so a demo never passes it off as real
    assert body["simulated_source_latency_ms"] == 0


class TestFactLookup:
    def _fact(self, pipeline, dept: str, status: str | None = None):
        facts = pipeline.state.store.facts_by_id.values()
        return next(
            f for f in facts if f.dept_code == dept and (status is None or f.status.value == status)
        )

    def test_a_reviewer_reads_one_record_with_its_source_and_status(self, pipeline):
        provisional = self._fact(pipeline, "CSE", "provisional")
        body = pipeline.login("registrar").get(f"/api/facts/{provisional.id}").json()
        assert body["id"] == provisional.id and body["status"] == "provisional"
        assert body["source_system"] and body["source_ref"] and body["used"] is False

    def test_a_final_record_counts_as_used(self, pipeline):
        final = self._fact(pipeline, "CSE", "final")
        assert pipeline.login("registrar").get(f"/api/facts/{final.id}").json()["used"] is True

    def test_a_hod_reads_their_own_department_but_another_looks_like_nothing(self, pipeline):
        own, other = self._fact(pipeline, "CSE"), self._fact(pipeline, "CIVIL")
        client = pipeline.login("hod_cse")
        assert client.get(f"/api/facts/{own.id}").status_code == 200
        hidden = client.get(f"/api/facts/{other.id}")
        missing = client.get("/api/facts/999999999")
        assert hidden.status_code == missing.status_code == 404
        assert "CIVIL" not in hidden.text

    def test_the_governing_council_cannot_read_records(self, pipeline):
        record = self._fact(pipeline, "CSE")
        assert pipeline.login("viewer").get(f"/api/facts/{record.id}").status_code == 403
