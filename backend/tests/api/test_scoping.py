"""A HOD never sees another department's record-level detail (rule in SPEC section 2, FR-15).

These tests read the raw response bodies, because the guarantee that matters is what is sent,
not what the UI chooses to draw.
"""

import json

import pytest

DEPARTMENTS = ["CSE", "AIML", "MCA", "ECE", "EEE", "MECH", "CIVIL", "BIOTECH"]
KPI_KEYS = [
    "AC_PASS_PCT", "AC_CO", "AC_PO", "AC_CURR", "RS_PUB_PF", "RS_CIT_PP", "RS_GRANT_PF",
    "PL_PCT", "PL_AVG", "PL_INT", "FN_UTIL", "FN_GRANT_UTIL", "FN_REV",
]  # fmt: skip
DOMAINS = ["academic", "research", "placement", "finance"]


def own_only(rows, mine):
    for row in rows:
        if row["dept_code"] in mine:
            assert row["access"] == "visible"
        else:
            assert row["access"] == "restricted", row["dept_code"]
            # a restricted row is identity only
            assert row["state"] is None and row["value"] is None
            assert row["inputs"] == [] and row["fact_ids"] == []
            assert row["as_of"] is None and row["reason"] is None and row["stale"] is False


@pytest.mark.parametrize("key", KPI_KEYS)
def test_a_hod_drilldown_holds_only_their_own_departments_detail(login, key):
    body = login("hod_cse").get(f"/api/kpis/{key}").json()
    assert body["access"] == "restricted"
    own_only(body["departments"], {"CSE"})
    assert {f["dept_code"] for f in body["facts"]} <= {"CSE"}
    assert body["spread"] is None  # a min and max would reveal other departments' extremes


def test_a_hod_is_told_that_detail_exists_without_seeing_it(login):
    body = login("hod_cse").get("/api/kpis/PL_PCT").json()
    assert body["facts_hidden"] > 0
    assert body["facts"] and all(f["dept_code"] == "CSE" for f in body["facts"])


@pytest.mark.parametrize("domain", DOMAINS)
def test_a_hod_domain_view_is_scoped_the_same_way(login, domain):
    body = login("hod_cse").get(f"/api/domains/{domain}").json()
    for kpi in body["kpis"]:
        own_only(kpi["departments"], {"CSE"})


def test_a_hod_still_sees_the_institution_figure_and_status(login):
    hod = login("hod_cse").get("/api/kpis").json()
    registrar = login("registrar").get("/api/kpis").json()
    for mine, full in zip(hod["kpis"], registrar["kpis"], strict=True):
        for field in ("value", "target", "status", "variance_abs"):
            assert mine[field] == full[field], (mine["key"], field)


def test_flags_name_only_the_departments_the_viewer_may_see_but_keep_the_count(login):
    cse = login("hod_cse").get("/api/kpis").json()["kpis"]
    civil = login("hod_civil").get("/api/kpis").json()["kpis"]
    cse_pl = next(k for k in cse if k["key"] == "PL_PCT")["flags"]["stale"]
    civil_pl = next(k for k in civil if k["key"] == "PL_PCT")["flags"]["stale"]
    assert cse_pl == {"departments": [], "total": 1}  # CIVIL's staleness is not CSE's business
    assert civil_pl == {"departments": ["CIVIL"], "total": 1}


def test_another_hods_values_appear_nowhere_in_a_hods_responses(login):
    registrar = login("registrar")
    full = json.dumps(registrar.get("/api/kpis/PL_PCT").json())
    civil_facts = {
        f["id"]
        for f in registrar.get("/api/kpis/PL_PCT").json()["facts"]
        if f["dept_code"] == "CIVIL"
    }
    assert civil_facts

    def mentions(blob: str, fact_id: int) -> bool:
        return f'"id": {fact_id},' in blob or f'"fact_ids": [{fact_id}' in blob

    # positive control: the check below must be able to find these ids when they are present
    assert all(mentions(full, fact_id) for fact_id in civil_facts)

    client = login("hod_cse")
    for url in ("/api/kpis/PL_PCT", "/api/domains/placement", "/api/data-health"):
        blob = json.dumps(client.get(url).json())
        assert '"CIVIL"' in blob  # the department list itself is not secret
        assert not any(mentions(blob, fact_id) for fact_id in civil_facts), url


def test_a_dean_sees_their_schools_departments_and_no_others(login):
    body = login("dean").get("/api/kpis/PL_PCT").json()
    own_only(body["departments"], {"CSE", "AIML", "MCA"})
    assert {f["dept_code"] for f in body["facts"]} <= {"CSE", "AIML", "MCA"}
    assert body["spread"] is None


@pytest.mark.parametrize("persona", ["registrar", "principal"])
def test_the_registrar_and_principal_see_every_department(login, persona):
    body = login(persona).get("/api/kpis/PL_PCT").json()
    assert body["access"] == "full"
    assert all(row["access"] == "visible" for row in body["departments"])
    assert body["spread"] is not None
    assert body["facts_hidden"] == 0


def test_data_health_hides_other_departments_cells_from_a_hod(login):
    body = login("hod_cse").get("/api/data-health").json()
    for cell in body["cells"]:
        if cell["dept_code"] == "CSE":
            assert cell["restricted"] is False and cell["state"] is not None
        else:
            assert cell["restricted"] is True
            assert cell["state"] is None and cell["as_of"] is None and cell["fact_count"] == 0
            assert cell["batch_ids"] == []
    assert body["summary"]["stale"] == 0  # CIVIL's stale placement is invisible to CSE
