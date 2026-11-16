def cells(client, period=None):
    url = "/api/data-health" + (f"?period={period}" if period else "")
    body = client.get(url).json()
    return body, {(c["dept_code"], c["domain"]): c for c in body["cells"]}


def test_t1_the_stale_placement_department_is_flagged_with_its_age(login):
    body, grid = cells(login("registrar"))
    civil = grid[("CIVIL", "placement")]
    assert civil["state"] == "stale"
    assert civil["age_days"] == 150
    assert body["stale_after_days"] == 90
    assert grid[("CSE", "placement")]["state"] == "fresh"


def test_t2_a_department_with_no_research_record_is_missing_not_fresh(login):
    _, grid = cells(login("registrar"))
    mech = grid[("MECH", "research")]
    assert mech["state"] == "missing"
    assert mech["fact_count"] == 0 and mech["as_of"] is None and mech["batch_ids"] == []
    assert grid[("MECH", "academic")]["state"] == "fresh"


def test_non_final_figures_are_counted_in_their_cell(login):
    _, grid = cells(login("registrar"))
    assert grid[("BIOTECH", "finance")]["non_final"]["pending_reconciliation"] == 1  # T8
    assert grid[("CSE", "finance")]["non_final"]["forecast"] == 1  # T4, the open quarter
    assert grid[("CSE", "placement")]["non_final"]["provisional"] > 0  # T3
    assert grid[("AIML", "placement")]["non_final"]["provisional"] == 0


def test_summary_counts_add_up_to_every_visible_cell(login):
    body, _ = cells(login("registrar"))
    summary = body["summary"]
    assert sum(summary.values()) == len(body["cells"]) == 8 * 5
    assert summary["stale"] == 1 and summary["missing"] == 1
    assert summary["closed"] == 0


def test_a_closed_period_is_never_called_stale(login):
    body, grid = cells(login("registrar"), "2024-25")
    assert body["is_current"] is False
    assert {c["state"] for c in grid.values()} == {"closed"}  # nothing missing in a closed year


def test_batches_name_their_source_file_and_owner(login):
    body, _ = cells(login("registrar"))
    assert body["batches"]
    for batch in body["batches"]:
        assert batch["source"] and batch["owner_office"] and batch["file_ref"]
        assert batch["row_count"] > 0 and batch["rejected_count"] == 0
        assert "2025-26" in batch["file_ref"] or batch["file_ref"] == "v_placement_summary"


def test_an_admin_sees_system_health_for_every_department(login):
    body, grid = cells(login("admin"))
    assert not any(c["restricted"] for c in body["cells"])
    assert grid[("CIVIL", "placement")]["state"] == "stale"


def test_a_dean_sees_only_their_schools_cells(login):
    body, _ = cells(login("dean"))
    visible = {c["dept_code"] for c in body["cells"] if not c["restricted"]}
    assert visible == {"CSE", "AIML", "MCA"}


def test_an_unknown_period_is_a_404(login):
    assert login("registrar").get("/api/data-health?period=1999-00").status_code == 404
