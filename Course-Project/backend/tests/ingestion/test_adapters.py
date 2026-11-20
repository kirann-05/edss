"""Reading a source: a file an office exports, or a query against a database the university has."""

import sqlite3

import pytest

from app.ingestion.adapters import (
    CsvAdapter,
    SqlAdapter,
    UnsafeQuery,
    assert_read_only,
    read_only_sqlite,
)
from app.ingestion.rows import FACT_REQUIRED, SchemaError

from .conftest import fact, fact_file


class TestCsv:
    def test_rows_come_back_under_the_canonical_columns_with_a_reference_to_the_row(self, tmp_path):
        path = fact_file(tmp_path, [fact(), fact(dept_code="ECE")])
        rows = CsvAdapter(path, required=FACT_REQUIRED).read()
        assert [r.ref for r in rows] == [
            "academic.csv:row 2",
            "academic.csv:row 3",
        ]  # row 1 is the header
        assert rows[1].values["dept_code"] == "ECE" and rows[0].values["value"] == "4600"

    def test_an_empty_cell_is_none_never_an_empty_string_or_zero(self, tmp_path):
        (row,) = CsvAdapter(fact_file(tmp_path, [fact()]), required=FACT_REQUIRED).read()
        assert row.values["numerator"] is None and row.values["unit"] is None

    def test_whitespace_around_a_cell_is_trimmed(self, tmp_path):
        path = tmp_path / "a.csv"
        path.write_text(
            "dept_code,metric_key,period_year,period_sub,value,status,as_of\n  CSE , acad.students_appeared ,2025-26,S1, 7 ,final,2026-09-09\n"
        )
        (row,) = CsvAdapter(path, required=FACT_REQUIRED).read()
        assert row.values["dept_code"] == "CSE" and row.values["value"] == "7"

    def test_the_byte_order_mark_that_excel_adds_does_not_break_the_first_column(self, tmp_path):
        path = tmp_path / "a.csv"
        path.write_bytes(
            b"\xef\xbb\xbfdept_code,metric_key,period_year,period_sub,value,status,as_of\nCSE,acad.students_appeared,2025-26,S1,7,final,2026-09-09\n"
        )
        (row,) = CsvAdapter(path, required=FACT_REQUIRED).read()
        assert row.values["dept_code"] == "CSE"

    def test_blank_lines_are_not_records(self, tmp_path):
        path = tmp_path / "a.csv"
        path.write_text(
            "dept_code,metric_key,period_year,period_sub,value,status,as_of\nCSE,acad.students_appeared,2025-26,S1,7,final,2026-09-09\n,,,,,,\n\n"
        )
        assert len(CsvAdapter(path, required=FACT_REQUIRED).read()) == 1

    def test_a_different_set_of_column_names_is_a_mapping_not_a_code_change(self, tmp_path):
        path = tmp_path / "exam.csv"
        path.write_text(
            "Department,Measure,Year,Term,Count,State,Date\nCSE,acad.students_appeared,2025-26,S1,7,final,2026-09-09\n"
        )
        mapping = {"dept_code": "Department", "metric_key": "Measure", "period_year": "Year",
                   "period_sub": "Term", "value": "Count", "status": "State", "as_of": "Date"}  # fmt: skip
        (row,) = CsvAdapter(path, required=FACT_REQUIRED, column_map=mapping).read()
        assert row.values["dept_code"] == "CSE" and row.values["value"] == "7"

    def test_column_names_are_matched_whatever_their_case(self, tmp_path):
        path = tmp_path / "a.csv"
        path.write_text(
            "DEPT_CODE,Metric_Key,PERIOD_YEAR,period_sub,VALUE,Status,AS_OF\nCSE,acad.students_appeared,2025-26,S1,7,final,2026-09-09\n"
        )
        assert CsvAdapter(path, required=FACT_REQUIRED).read()[0].values["status"] == "final"

    def test_a_missing_column_is_one_clear_error_naming_every_missing_column(self, tmp_path):
        path = tmp_path / "a.csv"
        path.write_text("dept_code,metric_key,value\nCSE,acad.students_appeared,7\n")
        with pytest.raises(SchemaError) as error:
            CsvAdapter(path, required=FACT_REQUIRED).read()
        assert error.value.missing == ["period_year", "period_sub", "status", "as_of"]
        assert "a.csv is missing the columns: period_year, period_sub, status, as_of" in str(
            error.value
        )

    def test_the_checksum_is_the_same_for_the_same_content_and_differs_when_it_changes(
        self, tmp_path
    ):
        a = CsvAdapter(fact_file(tmp_path, [fact()], "a.csv"), required=FACT_REQUIRED)
        same = CsvAdapter(fact_file(tmp_path, [fact()], "b.csv"), required=FACT_REQUIRED)
        other = CsvAdapter(fact_file(tmp_path, [fact(value="1")], "c.csv"), required=FACT_REQUIRED)
        assert a.checksum() == same.checksum() != other.checksum()


class TestSqlSafety:
    @pytest.mark.parametrize(
        "query",
        [
            "SELECT * FROM v",
            "select a, b from v where c = 'x'",
            "  WITH t AS (SELECT 1) SELECT * FROM t  ",
            "SELECT * FROM v;",
            "SELECT created_at, updated_by FROM v",  # words that merely contain a keyword
            "-- a note\nSELECT * FROM v",
        ],
    )
    def test_one_select_is_accepted(self, query):
        assert assert_read_only(query)

    @pytest.mark.parametrize(
        "query",
        [
            "DROP TABLE v",
            "DELETE FROM v",
            "UPDATE v SET a = 1",
            "INSERT INTO v VALUES (1)",
            "CREATE TABLE x (a int)",
            "SELECT * FROM v; DROP TABLE v",
            "SELECT * INTO copy FROM v",
            "SELECT 1 /* x */; DELETE FROM v",
            "PRAGMA writable_schema = 1",
            "ATTACH DATABASE 'x' AS y",
            "EXEC sp_who",
            "",
            "   ",
        ],
    )
    def test_anything_that_is_not_a_single_read_is_refused_before_a_connection_is_made(self, query):
        calls = []
        with pytest.raises(UnsafeQuery):
            SqlAdapter(lambda: calls.append(1), query, view="v", required=())
        assert calls == []


class TestSql:
    @pytest.fixture
    def database(self, tmp_path):
        path = tmp_path / "source.db"
        connection = sqlite3.connect(path)
        connection.execute(
            "CREATE TABLE v_placement (dept TEXT, metric TEXT, year TEXT, term TEXT, n TEXT, state TEXT, asof TEXT)"
        )
        connection.executemany(
            "INSERT INTO v_placement VALUES (?,?,?,?,?,?,?)",
            [("CSE", "plc.registered", "2025-26", "AY", "240", "final", "2026-09-15"),
             ("ECE", "plc.registered", "2025-26", "AY", "180", "final", "2026-09-15")],
        )  # fmt: skip
        connection.commit()
        connection.close()
        return path

    def adapter(self, database, **over):
        mapping = {"dept_code": "dept", "metric_key": "metric", "period_year": "year", "period_sub": "term",
                   "value": "n", "status": "state", "as_of": "asof"}  # fmt: skip
        args = dict(view="v_placement", required=("dept_code", "metric_key", "period_year", "value"),
                    column_map=mapping, make_read_only=read_only_sqlite)  # fmt: skip
        args.update(over)
        return SqlAdapter(lambda: sqlite3.connect(database), "SELECT * FROM v_placement", **args)

    def test_rows_are_read_under_the_canonical_columns(self, database):
        rows = self.adapter(database).read()
        assert [r.values["dept_code"] for r in rows] == ["CSE", "ECE"]
        assert rows[0].values["value"] == "240" and rows[0].values["status"] == "final"

    def test_a_record_in_a_database_is_referenced_by_its_key_not_a_row_number(self, database):
        assert self.adapter(database).read()[0].ref == "sql:v_placement:CSE/2025-26/plc.registered"

    def test_a_missing_column_is_one_clear_error(self, database):
        with pytest.raises(SchemaError, match="v_placement is missing the column: source_ref"):
            self.adapter(database, required=("dept_code", "source_ref")).read()

    def test_the_connection_is_closed_even_when_the_query_fails(self, database):
        closed = []

        class Spy:
            def __init__(self, inner):
                self.inner = inner

            def cursor(self):
                return self.inner.cursor()

            def execute(self, *args):
                return self.inner.execute(*args)

            def close(self):
                closed.append(True)
                self.inner.close()

        adapter = SqlAdapter(
            lambda: Spy(sqlite3.connect(database)),
            "SELECT * FROM missing_table",
            view="x",
            required=(),
        )
        with pytest.raises(sqlite3.OperationalError):
            adapter.read()
        assert closed == [True]

    def test_the_checksum_follows_the_content_of_the_source(self, database):
        before = self.adapter(database).checksum()
        assert before == self.adapter(database).checksum()
        connection = sqlite3.connect(database)
        connection.execute("UPDATE v_placement SET n = '241' WHERE dept = 'CSE'")
        connection.commit()
        connection.close()
        assert self.adapter(database).checksum() != before

    def test_a_connection_made_read_only_cannot_write_even_if_a_query_were_to_try(self, database):
        connection = sqlite3.connect(database)
        read_only_sqlite(connection)
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM v_placement")
        connection.close()
