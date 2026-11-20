import csv
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from app.domain.models import Department
from app.ingestion.export import export_dataset
from app.ingestion.rows import FACT_COLUMNS, PUBLICATION_COLUMNS
from app.synthetic.generator import generate

TODAY = date(2026, 10, 1)
DEPARTMENTS = (
    Department(code="CSE", name="Computer Science", school="Computing"),
    Department(code="ECE", name="Electronics", school="Engineering"),
)


@pytest.fixture(scope="session")
def dataset():
    return generate(reference_date=TODAY)


@pytest.fixture(scope="session")
def exported(tmp_path_factory, dataset) -> Path:
    folder = tmp_path_factory.mktemp("export")
    export_dataset(dataset, folder)
    return folder


def write_csv(path: Path, header, rows) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def fact(**over) -> dict:
    """A good fact row in the canonical columns. Tests change one thing at a time."""
    row = {
        "dept_code": "CSE", "metric_key": "acad.students_appeared", "period_year": "2025-26",
        "period_sub": "S1", "value": "4600", "status": "final", "as_of": "2026-09-09",
        "numerator": "", "denominator": "", "unit": "", "source_ref": "",
    }  # fmt: skip
    row.update(over)
    return row


def fact_file(tmp_path: Path, rows: list[dict], name: str = "academic.csv") -> Path:
    return write_csv(
        tmp_path / name, FACT_COLUMNS, [[r.get(c, "") for c in FACT_COLUMNS] for r in rows]
    )


def publication_file(tmp_path: Path, rows: list[dict], name: str = "publications.csv") -> Path:
    return write_csv(
        tmp_path / name,
        PUBLICATION_COLUMNS,
        [[r.get(c, "") for c in PUBLICATION_COLUMNS] for r in rows],
    )


def sqlite_with(tmp_path: Path, folder: Path) -> Path:
    """The exported CSVs loaded into a SQLite file, one table per domain: a stand-in source database."""
    db = tmp_path / "source.db"
    connection = sqlite3.connect(db)
    for domain in ("academic", "research", "placement", "finance", "reference"):
        with (folder / f"{domain}.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            connection.execute(
                f"CREATE TABLE v_{domain} ({', '.join(f'{c} TEXT' for c in header)})"
            )
            connection.executemany(
                f"INSERT INTO v_{domain} VALUES ({', '.join('?' for _ in header)})", list(reader)
            )
    with (folder / "publications.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        connection.execute(
            f"CREATE TABLE v_publications ({', '.join(f'{c} TEXT' for c in header)})"
        )
        connection.executemany(
            f"INSERT INTO v_publications VALUES ({', '.join('?' for _ in header)})", list(reader)
        )
    connection.commit()
    connection.close()
    return db
