"""Write a dataset out as the files a source office would send, plus the manifest that names them.

For the synthetic dataset this makes a runnable sample (`data/sample`): the same code that reads a
real folder of exports reads it, which is what proves the adapters and the validator work. It is
also the model for what a data owner is asked to supply (docs/DATA_CONTRACT.md).
"""

import csv
from pathlib import Path

import yaml

from app.domain.dataset import Dataset
from app.domain.enums import Domain
from app.ingestion.rows import DEPARTMENT_COLUMNS, FACT_COLUMNS, PUBLICATION_COLUMNS

_FILES = {
    Domain.ACADEMIC: "academic.csv",
    Domain.RESEARCH: "research.csv",
    Domain.PLACEMENT: "placement.csv",
    Domain.FINANCE: "finance.csv",
    Domain.REFERENCE: "reference.csv",
}


def _write(path: Path, header: tuple[str, ...], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def export_templates(folder: Path) -> None:
    """Files with only the header and, for academic, one worked example row, for a data owner to fill in."""
    folder.mkdir(parents=True, exist_ok=True)
    example = [
        "CSE",
        "acad.students_appeared",
        "2025-26",
        "S1",
        "4600",
        "final",
        "2026-09-09",
        "",
        "",
        "students",
        "your own row reference",
    ]
    for domain, name in _FILES.items():
        _write(folder / name, FACT_COLUMNS, [example] if domain is Domain.ACADEMIC else [])
    _write(
        folder / "publications.csv", PUBLICATION_COLUMNS,
        [["10.1000/example.doi", "An example paper", "2025-26", "final", "CSE;ECE", "An Example Journal", "Scopus"]],
    )  # fmt: skip
    _write(
        folder / "departments.csv",
        DEPARTMENT_COLUMNS,
        [["CSE", "Computer Science and Engineering", "School of Computing"]],
    )


def export_dataset(dataset: Dataset, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    _write(
        folder / "departments.csv", DEPARTMENT_COLUMNS,
        [[d.code, d.name, d.school] for d in dataset.departments],
    )  # fmt: skip

    sources = {s.id: s for s in dataset.source_systems}
    entries = []
    for domain, filename in _FILES.items():
        facts = [f for f in dataset.facts if f.domain is domain]
        if not facts:
            continue
        _write(
            folder / filename, FACT_COLUMNS,
            [
                [
                    f.dept_code, f.metric_key, f.period_year, f.period_sub, format(f.value, "f"), f.status.value,
                    f.as_of.isoformat(), "" if f.numerator is None else format(f.numerator, "f"),
                    "" if f.denominator is None else format(f.denominator, "f"), f.unit, f.source_ref,
                ]
                for f in facts
            ],
        )  # fmt: skip
        source = sources[facts[0].source_system_id]
        entry = {
            "domain": domain.value,
            "name": source.name,
            "owner_office": source.owner_office,
            "kind": "csv",
            "file": filename,
        }
        if domain is Domain.RESEARCH:
            entry["publications"] = "publications.csv"
        entries.append(entry)

    _write(
        folder / "publications.csv", PUBLICATION_COLUMNS,
        [
            [p.dedup_key, p.title, p.period_year, p.status.value, ";".join(p.dept_codes), p.venue, p.indexing]
            for p in dataset.publications
        ],
    )  # fmt: skip
    (folder / "manifest.yml").write_text(
        yaml.safe_dump({"departments": "departments.csv", "sources": entries}, sort_keys=False)
    )
