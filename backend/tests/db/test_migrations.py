"""L5b: the first migration builds every table in the data contract, and takes it down again."""

import os
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.schema import metadata

pytestmark = pytest.mark.db
ALEMBIC_INI = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")


def test_every_table_in_the_contract_exists(migrated):
    assert set(inspect(migrated).get_table_names()) == set(metadata.tables) | {"alembic_version"}


def test_the_database_matches_the_schema_with_nothing_left_to_migrate(migrated):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    with migrated.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), metadata) == []


def test_a_figure_keeps_every_digit(migrated):
    with migrated.begin() as conn:
        value = conn.execute(text("select cast('74.96000000000000000001' as numeric)")).scalar_one()
        assert value == Decimal("74.96000000000000000001")
        kind = conn.execute(
            text(
                "select data_type from information_schema.columns where table_name = 'metric_fact' and column_name = 'value'"
            )
        ).scalar_one()
    assert kind == "numeric"


def test_a_status_the_contract_does_not_have_is_refused(migrated):
    with pytest.raises(IntegrityError, match="ck_metric_fact_status"), migrated.begin() as conn:
        conn.execute(
            text("insert into department (code, name) values ('ZZZ', 'A test department')")
        )
        source = conn.execute(
            text(
                "insert into source_system (name, owner_office, kind) values ('test', 'o', 'csv') returning id"
            )
        ).scalar_one()
        batch = conn.execute(
            text(
                "insert into ingest_batch (source_system_id, domain, data_mode, started_at, file_ref, checksum, "
                "ingested_by) values (:s, 'placement', 'synthetic', now(), 'f', 'c', 'test') returning id"
            ),
            {"s": source},
        ).scalar_one()
        conn.execute(
            text(
                "insert into metric_fact (batch_id, domain, metric_key, dept_code, period_year, period_sub, value, "
                "unit, status, as_of, source_system_id, source_ref, recorded_at) values (:b, 'placement', "
                "'plc.registered', 'ZZZ', '2025-26', 'AY', 1, 'students', 'approved', current_date, :s, 'r', now())"
            ),
            {"b": batch, "s": source},
        )


def test_a_definition_that_is_not_a_placeholder_must_name_its_approver(migrated):
    with (
        pytest.raises(IntegrityError, match="ck_kpi_definition_approved"),
        migrated.begin() as conn,
    ):
        conn.execute(
            text(
                "insert into kpi_definition (key, name, framework, domain, domain_tags, formula, unit, placeholder) "
                "values ('X', 'x', 'NIRF', 'research', '{research}', 'f', 'u', false)"
            )
        )


def test_pgvector_is_on(migrated):
    with migrated.connect() as conn:
        assert conn.execute(
            text("select extversion from pg_extension where extname = 'vector'")
        ).scalar_one()


def test_downgrade_takes_every_table_away(scratch_db, migrated, monkeypatch_module):
    command.downgrade(Config(ALEMBIC_INI), "base")
    assert set(inspect(migrated).get_table_names()) == {"alembic_version"}
    command.upgrade(Config(ALEMBIC_INI), "head")  # and back, so the order of tests does not matter
