"""A folder of exports and a manifest that says what each file is.

    departments: departments.csv
    sources:
      - {domain: academic, name: "Examination Section results export",
         owner_office: "Controller of Examinations", file: academic.csv}
      - {domain: research, ..., file: research.csv, publications: publications.csv}
    column_map is optional per source: {dept_code: "Department", value: "Count"}

The manifest and the files are the whole of what changes when real data replaces the synthetic
set. Nothing in the agents, the engine or the UI depends on them (rule 6).
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from app.domain.enums import Domain
from app.domain.models import Department
from app.ingestion.adapters import CsvAdapter
from app.ingestion.loader import IngestResult, Ledger
from app.ingestion.rows import DEPARTMENT_COLUMNS, FACT_REQUIRED, PUBLICATION_REQUIRED, SchemaError

TEMPLATE_MARKER = "CHANGE ME"  # what the templates' manifest says until a person fills it in


class ManifestError(ValueError):
    pass


@dataclass
class FolderResult:
    ledger: Ledger
    results: list[tuple[str, IngestResult]] = field(default_factory=list)  # (label, result)
    errors: list[str] = field(default_factory=list)  # a whole file that could not be read at all

    @property
    def rejected(self) -> int:
        return sum(len(r.rejects) for _, r in self.results)

    @property
    def accepted(self) -> int:
        return sum(r.accepted for _, r in self.results)


def read_departments(path: Path) -> list[Department]:
    rows = CsvAdapter(path, required=DEPARTMENT_COLUMNS).read()
    seen: set[str] = set()
    departments = []
    for row in rows:
        code = (row.values.get("code") or "").upper()
        if not code or not row.values.get("name"):
            raise ManifestError(f"{row.ref}: a department needs a code and a name")
        if code in seen:
            raise ManifestError(f"{row.ref}: department {code} is listed twice")
        seen.add(code)
        departments.append(
            Department(
                code=code, name=row.values["name"] or "", school=row.values.get("school") or ""
            )
        )
    if not departments:
        raise ManifestError(f"{path.name} lists no departments")
    return departments


def ingest_folder(
    folder: Path,
    today: date,
    data_mode: str = "real",
    ingested_by: str = "ingest",
    ledger: Ledger | None = None,
) -> FolderResult:
    """Read a folder into a ledger. Given an existing ledger, add to it: a file that has not
    changed adds nothing, a file that has changed becomes a new batch, and every earlier record,
    with the id a brief may already cite, stays exactly as it was."""
    manifest_path = folder / "manifest.yml"
    if not manifest_path.exists():
        raise ManifestError(f"{folder} has no manifest.yml")
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    departments = read_departments(folder / manifest.get("departments", "departments.csv"))
    if ledger is None:
        ledger = Ledger(departments, today, data_mode)
    elif {d.code for d in departments} != {d.code for d in ledger.departments}:
        raise ManifestError(
            "the list of departments has changed, which needs the server restarted so every "
            "department is known from the start"
        )
    else:
        ledger.today = today  # the day this reading happened, which freshness is judged against
    outcome = FolderResult(ledger)

    for entry in manifest.get("sources", []):
        try:
            domain = Domain(entry["domain"])
        except (KeyError, ValueError):
            raise ManifestError(
                f"a source needs a domain from {[d.value for d in Domain]}: {entry}"
            ) from None
        if any(TEMPLATE_MARKER in str(entry.get(k, "")) for k in ("name", "owner_office")):
            # these words travel with every figure as its source, so they must be true
            raise ManifestError(
                f"the {domain.value} source still says {TEMPLATE_MARKER!r}: write in manifest.yml "
                "which system the file was exported from and which office owns it"
            )
        source = ledger.source(entry["name"], entry["owner_office"], entry.get("kind", "csv"))
        column_map = entry.get("column_map")
        for label, filename, required, ingest in (
            (f"{domain.value} facts", entry.get("file"), FACT_REQUIRED, "facts"),
            (
                f"{domain.value} publications",
                entry.get("publications"),
                PUBLICATION_REQUIRED,
                "publications",
            ),
        ):
            if not filename:
                continue
            mapping = (
                entry.get("publications_column_map", column_map)
                if ingest == "publications"
                else column_map
            )
            adapter = CsvAdapter(folder / filename, required=required, column_map=mapping)
            try:
                result = (
                    ledger.ingest_facts(adapter, source, domain, ingested_by)
                    if ingest == "facts"
                    else ledger.ingest_publications(adapter, source, ingested_by)
                )
            except (SchemaError, FileNotFoundError) as error:
                outcome.errors.append(f"{label}: {error}")
                continue
            outcome.results.append((f"{label} ({filename})", result))
    return outcome
