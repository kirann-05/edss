"""Source adapters: one class per kind of source, each reading rows under the canonical columns.

CsvAdapter reads a file an office exports. SqlAdapter runs a query against a database the
university already has, read-only. Neither knows what a KPI is. They are the only things that
change when a real source replaces the synthetic one (docs/DATA_CONTRACT.md: "If the university's
columns differ, change the adapter, never the agents").

On SQL: the guard here is a second line of defence. The first is the database account, which
should have SELECT and nothing else. A guard in code can be bypassed by a cleverer query, an
account that cannot write cannot be argued with.
"""

import csv
import hashlib
import re
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from app.ingestion.rows import RawRow, SchemaError


class SourceAdapter(Protocol):
    kind: str  # csv or sql
    file_ref: str  # what the batch is called: a file name or a view name

    def read(self) -> list[RawRow]: ...

    def checksum(self) -> str:
        """A fingerprint of what would be read. The same fingerprint is the same content."""
        ...


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _canonical(columns: Sequence[str], column_map: Mapping[str, str] | None) -> dict[str, str]:
    """For each canonical column wanted, which source column holds it. Defaults to the same name."""
    available = {c.strip().lower(): c for c in columns}
    mapping: dict[str, str] = {}
    for canonical in ("dept_code", "metric_key", "period_year", "period_sub", "value", "status", "as_of",
                      "numerator", "denominator", "unit", "source_ref", "dedup_key", "title", "venue",
                      "indexing", "dept_codes", "code", "name", "school"):  # fmt: skip
        wanted = (column_map or {}).get(canonical, canonical).strip().lower()
        if wanted in available:
            mapping[canonical] = available[wanted]
    return mapping


class CsvAdapter:
    kind = "csv"

    def __init__(
        self,
        path: Path | str,
        *,
        required: Sequence[str],
        column_map: Mapping[str, str] | None = None,
    ) -> None:
        self._path = Path(path)
        self._required = tuple(required)
        self._column_map = column_map
        self.file_ref = self._path.name

    def checksum(self) -> str:
        return hashlib.sha256(self._path.read_bytes()).hexdigest()[:16]

    def read(self) -> list[RawRow]:
        # utf-8-sig, because Excel puts a byte order mark at the start of a CSV it saves
        with self._path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            mapping = _canonical(reader.fieldnames or [], self._column_map)
            missing = [c for c in self._required if c not in mapping]
            if missing:
                raise SchemaError(self.file_ref, missing)
            rows = []
            for number, record in enumerate(reader, start=2):  # row 1 is the header, as in Excel
                if not any(_clean(v) for v in record.values()):
                    continue  # a blank line is not a record
                values = {
                    canonical: _clean(record.get(source)) for canonical, source in mapping.items()
                }
                rows.append(RawRow(ref=f"{self.file_ref}:row {number}", values=values))
        return rows


_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|merge|call|exec|execute|"
    r"attach|detach|pragma|copy|vacuum|into)\b",
    re.IGNORECASE,
)


class UnsafeQuery(ValueError):
    """A query that is not a single read."""


def assert_read_only(query: str) -> str:
    """Only one SELECT (or WITH ... SELECT) is accepted. See the module note on what this is for."""
    text = re.sub(r"--[^\n]*|/\*.*?\*/", " ", query, flags=re.DOTALL).strip().rstrip(";").strip()
    if not re.match(r"(?is)^(select|with)\b", text):
        raise UnsafeQuery("a source query must be a single SELECT")
    if ";" in text:
        raise UnsafeQuery("a source query must be one statement")
    found = _FORBIDDEN.search(text)
    if found:
        raise UnsafeQuery(
            f"a source query may only read, but it contains {found.group().upper()!r}"
        )
    return text


def read_only_sqlite(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA query_only = ON")


class SqlAdapter:
    kind = "sql"

    def __init__(
        self,
        connect: Callable[[], Any],
        query: str,
        *,
        view: str,
        required: Sequence[str],
        column_map: Mapping[str, str] | None = None,
        make_read_only: Callable[[Any], None] | None = None,
    ) -> None:
        self._connect = connect
        self._query = assert_read_only(query)
        self._required = tuple(required)
        self._column_map = column_map
        self._make_read_only = make_read_only
        self.file_ref = view

    def _fetch(self) -> tuple[list[str], list[tuple[Any, ...]]]:
        connection = self._connect()
        try:
            if self._make_read_only is not None:
                self._make_read_only(connection)
            cursor = connection.cursor()
            cursor.execute(self._query)
            columns = [d[0] for d in cursor.description]
            return columns, [tuple(r) for r in cursor.fetchall()]
        finally:
            connection.close()

    def checksum(self) -> str:
        columns, rows = self._fetch()
        digest = hashlib.sha256(repr((columns, rows)).encode())
        return digest.hexdigest()[:16]

    def read(self) -> list[RawRow]:
        columns, records = self._fetch()
        mapping = _canonical(columns, self._column_map)
        missing = [c for c in self._required if c not in mapping]
        if missing:
            raise SchemaError(self.file_ref, missing)
        index = {canonical: columns.index(source) for canonical, source in mapping.items()}
        rows = []
        for number, record in enumerate(records, start=1):
            values = {canonical: _clean(record[i]) for canonical, i in index.items()}
            # a record in a database is named by its key, which is more use than a row number
            if (
                values.get("source_ref") is None
                and {"dept_code", "period_year", "metric_key"} <= values.keys()
            ):
                ref = f"sql:{self.file_ref}:{values['dept_code']}/{values['period_year']}/{values['metric_key']}"
            else:
                ref = f"sql:{self.file_ref}:row {number}"
            rows.append(RawRow(ref=ref, values=values))
        return rows
