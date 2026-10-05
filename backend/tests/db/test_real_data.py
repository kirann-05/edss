"""R1: the university's exports loaded into PostgreSQL, and the app in real mode (D32 to D34)."""

import csv
import secrets
import shutil
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.agents.llm import DataModeViolation
from app.core.security import hash_password
from app.db.checkpoints import setup as setup_checkpoints
from app.db.dataset_store import save_dataset
from app.db.real_data import load_real_folder
from app.db.urls import owner_url
from app.ingestion.export import export_dataset
from app.ingestion.manifest import ManifestError
from app.kpi.loader import PLACEHOLDER_MARKER, load_seed_definitions, load_seed_targets
from app.main import create_app
from app.synthetic.generator import generate
from tests.api.conftest import PASSWORD, REF, make_settings
from tests.database_fixtures import ALEMBIC_INI, _admin

pytestmark = pytest.mark.db
TODAY = date(2026, 10, 3)


@pytest.fixture(scope="module")
def real_db(scratch_db):
    """A database of its own: going real is one-way, so it must not touch the shared one."""
    name = f"edss_real_{secrets.token_hex(4)}"
    with _admin() as admin:
        admin.execute(f'create database "{name}"')
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("EDSS_DB_NAME", name)
        command.upgrade(Config(ALEMBIC_INI), "head")
        setup_checkpoints(owner_url(database=name))
        engine = create_engine(owner_url(database=name))
        with engine.begin() as conn:  # the synthetic sample first, as a server would have it
            save_dataset(
                conn, generate(reference_date=REF), load_seed_definitions(), load_seed_targets()
            )
        yield engine, name
        engine.dispose()
    with _admin() as admin:
        admin.execute(f'drop database "{name}" with (force)')


@pytest.fixture(scope="module")
def folder(tmp_path_factory) -> Path:
    """The university's folder: here the sample's files, with BIOTECH left off the department list."""
    path = tmp_path_factory.mktemp("real")
    export_dataset(generate(reference_date=REF), path)
    rows = list(csv.DictReader((path / "departments.csv").open()))
    with (path / "departments.csv").open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(r for r in rows if r["code"] != "BIOTECH")
    return path


@pytest.fixture(scope="module")
def first_load(real_db, folder):
    engine, _ = real_db
    with engine.connect() as conn:
        before = conn.execute(text("select coalesce(max(id), 0) from metric_fact")).scalar_one()
        synthetic = conn.execute(
            text("select count(*) from ingest_batch where data_mode = 'synthetic'")
        ).scalar_one()
    return load_real_folder(engine, folder, TODAY, "test"), before, synthetic


def test_the_first_load_adds_the_records_and_switches_the_database_to_real(first_load, real_db):
    load, before, synthetic = first_load
    engine, _ = real_db
    assert load.switched_to_real and load.written["facts"] > 0
    assert load.outcome.rejected > 0  # every BIOTECH row is refused, with its reason, not added
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("select value from system_config where key = 'data_mode'")
            ).scalar_one()
            == "real"
        )
        real_min = conn.execute(
            text(
                "select min(f.id) from metric_fact f join ingest_batch b on b.id = f.batch_id where b.data_mode = 'real'"
            )
        ).scalar_one()
        kept = conn.execute(
            text("select count(*) from ingest_batch where data_mode = 'synthetic'")
        ).scalar_one()
        actions = conn.execute(text("select action from audit_log order by id")).scalars().all()
    assert real_min > before  # new ids above every id already used
    assert kept == synthetic  # the synthetic records are archived, not deleted
    assert {"data.load_real", "data.mode_real"} <= set(actions)


def test_the_synthetic_personas_are_switched_off(first_load, real_db):
    engine, _ = real_db
    with engine.connect() as conn:
        active = conn.execute(
            text("select count(*) from app_user where email like '%@edss.test' and active")
        ).scalar_one()
    assert active == 0


def test_loading_the_same_folder_again_adds_nothing(first_load, real_db, folder):
    again = load_real_folder(real_db[0], folder, TODAY, "test")
    assert again.written["batches"] == 0 and again.written["facts"] == 0
    assert not again.switched_to_real


def test_a_changed_file_is_a_new_batch_and_the_old_records_stay(first_load, real_db, folder):
    engine, _ = real_db
    with engine.connect() as conn:
        held = conn.execute(text("select count(*) from metric_fact")).scalar_one()
    placement = folder / "placement.csv"
    lines = placement.read_text().splitlines()
    header, first, *rest = lines
    cells = first.split(",")
    columns = header.split(",")
    cells[columns.index("value")] = str(float(cells[columns.index("value")]) + 1)
    placement.write_text("\n".join([header, ",".join(cells), *rest]) + "\n")
    changed = load_real_folder(engine, folder, TODAY, "test")
    assert changed.written["batches"] == 1
    with engine.connect() as conn:
        now = conn.execute(text("select count(*) from metric_fact")).scalar_one()
    assert now == held + changed.written["facts"]  # added, never replaced


def start(name, **overrides):
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("EDSS_DB_NAME", name)
        return create_app(make_settings(edss_database=True, **overrides), today=TODAY)


def test_the_app_refuses_to_start_when_the_env_and_the_database_disagree(first_load, real_db):
    with pytest.raises(RuntimeError, match="Set DATA_MODE=real"):
        start(real_db[1])


def test_real_mode_needs_a_real_administrator(first_load, real_db):
    with pytest.raises(RuntimeError, match="needs an administrator"):
        start(real_db[1], data_mode="real")


@pytest.fixture(scope="module")
def real_app(first_load, real_db):
    engine, name = real_db
    with engine.begin() as conn:
        conn.execute(
            text(
                "insert into app_user (id, email, name, role, active, password_hash, session_version) "
                "values (100, 'it.admin@university.example', 'IT Administrator', 'admin', true, :h, 0)"
            ),
            {"h": hash_password("a-long-admin-password")},
        )
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("EDSS_DB_NAME", name)
        app = create_app(
            make_settings(edss_database=True, data_mode="real", edss_demo_login=True), today=TODAY
        )
        yield app, TestClient(app)


def test_in_real_mode_only_the_real_records_and_the_real_department_list_are_read(
    real_app, real_db
):
    app, _ = real_app
    store = app.state.edss.store
    assert "BIOTECH" not in [d.code for d in store.dataset.departments]
    assert all(b.data_mode == "real" for b in store.dataset.batches)
    with real_db[0].connect() as conn:
        real_facts = conn.execute(
            text(
                "select count(*) from metric_fact f join ingest_batch b on b.id = f.batch_id where b.data_mode = 'real'"
            )
        ).scalar_one()
    assert len(store.dataset.facts) == real_facts


def test_in_real_mode_no_demo_sign_in_no_synthetic_persona_and_no_invented_history(real_app):
    app, client = real_app
    assert (
        client.post("/api/auth/demo-login", json={"email": "registrar@edss.test"}).status_code
        == 404
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "registrar@edss.test", "password": PASSWORD},
        ).status_code
        == 401
    )
    assert app.state.edss.archive.all() == []
    assert app.state.edss.system_config.data_mode() == "real"


def test_the_real_administrator_can_sign_in(real_app):
    _, client = real_app
    signed = client.post(
        "/api/auth/login",
        json={"email": "it.admin@university.example", "password": "a-long-admin-password"},
    )
    assert signed.status_code == 200, signed.text


def test_in_real_mode_the_archive_fills_only_with_reports_published_here(real_app):
    from app.governance.service import Decision

    app, _ = real_app
    state = app.state.edss
    assert state.archive.all() == []
    # no real approver role exists yet in this test database, so publish as an approver made here
    from app.domain.enums import Role

    approver = state.users.create(
        email="principal@university.example", name="The Principal", role=Role.PRINCIPAL,
        password="a-long-principal-password",
    )  # fmt: skip
    registrar = state.users.create(
        email="registrar@university.example", name="The Registrar", role=Role.REGISTRAR,
        password="a-long-registrar-password",
    )  # fmt: skip
    record = state.runs.create(
        registrar, "Placement and research brief for the Governing Council for 2025-26"
    )
    if record.questions:
        record = state.runs.skip_questions(registrar, record.id)
    state.runs.lock(registrar, record.id, [])
    from app.services.demo_state import _finish

    done = _finish(state, state.runs.get(record.id))
    assert done.brief_id, done.error
    version = state.governance.decide(done.brief_id, approver, Decision(kind="approve")).version
    assert [p.id for p in state.archive.all()] == [f"report-v{version.version}"]


def test_real_mode_will_not_start_with_a_hosted_model(real_app, real_db):
    with pytest.raises(DataModeViolation, match="never allowed when data mode is real"):
        start(
            real_db[1], data_mode="real", llm_provider="hosted", allow_hosted_llm=True,
            llm_base_url="https://models.example.com/v1",
        )  # fmt: skip


def test_an_env_setting_alone_never_makes_a_database_real(scratch_db, migrated):
    # a fresh database that has never held real data: starting with DATA_MODE=real is refused,
    # and the stored mode stays synthetic, so the synthetic app can still start afterwards
    name = f"edss_fresh_{secrets.token_hex(4)}"
    with _admin() as admin:
        admin.execute(f'create database "{name}"')
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("EDSS_DB_NAME", name)
            command.upgrade(Config(ALEMBIC_INI), "head")
            setup_checkpoints(owner_url(database=name))
            engine = create_engine(owner_url(database=name))
            with engine.begin() as conn:
                save_dataset(
                    conn, generate(reference_date=REF), load_seed_definitions(), load_seed_targets()
                )
            with pytest.raises(RuntimeError, match="holds no real data"):
                create_app(make_settings(edss_database=True, data_mode="real"), today=TODAY)
            with engine.connect() as conn:
                stored = conn.execute(
                    text("select value from system_config where key = 'data_mode'")
                ).scalar_one()
            engine.dispose()
            assert stored == "synthetic"
            create_app(
                make_settings(edss_database=True), today=TODAY
            )  # still starts in synthetic mode
    finally:
        with _admin() as admin:
            admin.execute(f'drop database "{name}" with (force)')


@pytest.fixture
def bare_db(scratch_db):
    """A server where only the migrations ran: no synthetic sample was ever loaded."""
    name = f"edss_bare_{secrets.token_hex(4)}"
    with _admin() as admin:
        admin.execute(f'create database "{name}"')
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("EDSS_DB_NAME", name)
        command.upgrade(Config(ALEMBIC_INI), "head")
        engine = create_engine(owner_url(database=name))
        yield engine
        engine.dispose()
    with _admin() as admin:
        admin.execute(f'drop database "{name}" with (force)')


def counts(engine):
    with engine.connect() as conn:
        return {
            table: conn.execute(text(f"select count(*) from {table}")).scalar_one()
            for table in ("ingest_batch", "metric_fact", "kpi_definition", "kpi_target")
        } | {
            "mode": conn.execute(
                text("select value from system_config where key = 'data_mode'")
            ).scalar_one_or_none()
        }


def test_a_folder_without_a_manifest_is_refused(bare_db, tmp_path):
    with pytest.raises(ManifestError, match="has no manifest.yml"):
        load_real_folder(bare_db, tmp_path, TODAY, "test")


def test_a_folder_with_a_file_that_cannot_be_read_writes_nothing(bare_db, folder, tmp_path):
    broken = tmp_path / "broken"
    shutil.copytree(folder, broken)
    (broken / "finance.csv").unlink()
    before = counts(bare_db)
    load = load_real_folder(bare_db, broken, TODAY, "test")
    assert any(e.startswith("finance facts") for e in load.outcome.errors)
    assert not load.switched_to_real and not any(load.written.values())
    assert counts(bare_db) == before  # the other three areas read fine, and still nothing was added


def test_a_first_real_load_on_a_bare_server_brings_the_placeholder_definitions(bare_db, folder):
    load = load_real_folder(bare_db, folder, TODAY, "test")
    assert load.switched_to_real and load.written["facts"] > 0
    after = counts(bare_db)
    assert after["mode"] == "real"
    assert after["kpi_definition"] == len(load_seed_definitions())
    assert after["kpi_target"] == len(load_seed_targets())
    with bare_db.connect() as conn:
        notes = conn.execute(text("select placeholder, note from kpi_definition")).all()
    assert all(placeholder and PLACEHOLDER_MARKER in note for placeholder, note in notes)  # rule 12


def test_the_app_runs_in_real_mode_on_a_bare_server_after_the_first_load(bare_db, folder):
    load_real_folder(bare_db, folder, TODAY, "test")
    name = bare_db.url.database
    setup_checkpoints(owner_url(database=name))
    with bare_db.begin() as conn:
        conn.execute(
            text(
                "insert into app_user (id, email, name, role, active, password_hash, session_version) "
                "values (1, 'it.admin@university.example', 'IT Administrator', 'admin', true, :h, 0)"
            ),
            {"h": hash_password("a-long-admin-password")},
        )
    client = TestClient(start(name, data_mode="real"))
    signed_in = client.post(
        "/api/auth/login",
        json={"email": "it.admin@university.example", "password": "a-long-admin-password"},
    )
    assert signed_in.status_code == 200
    assert client.get("/api/system/status").json()["data_mode"] == "real"
    created = client.post(
        "/api/admin/users",
        json={
            "email": "registrar@university.example",
            "name": "Registrar",
            "role": "registrar",
            "password": "a-long-registrar-password",
        },
    )
    assert created.status_code == 201
    registrar = TestClient(client.app)
    registrar.post(
        "/api/auth/login",
        json={"email": "registrar@university.example", "password": "a-long-registrar-password"},
    )
    kpis = registrar.get("/api/kpis")
    assert kpis.status_code == 200
    assert len(kpis.json()["kpis"]) == len(load_seed_definitions())
