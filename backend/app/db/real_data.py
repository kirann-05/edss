"""The university's own exports, loaded into PostgreSQL (CHECKLIST R1, decisions D32 to D34).

From the command line only (scripts/ingest.py --db), by the people who run the server. A folder
goes through the same ingestion as everywhere else: the manifest, the validator with a plain reason
for every refused row, and the reconciliation report. What is accepted is only ever added:

- a file that has not changed adds nothing, a changed file is a new batch, and earlier records
  stay exactly as they were, so a record an approved brief cites never changes (D26);
- new records take ids above every id already used, by either mode;
- the manifest's departments become the list the app shows, in its order (D33).

The first real load switches the database's data mode to real, once and on purpose (D32). From then
the synthetic records are kept, archived, and never read; the synthetic personas are switched off,
because their shared password and .test addresses must not open real data; and every load is a
row in the audit log.
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import Engine, func, insert, select, text

from app.db import schema as t
from app.db.audit_store import DbAuditLog
from app.db.dataset_store import insert_records, load_dataset, real_data_present
from app.domain.enums import FactStatus
from app.domain.models import SourceSystem
from app.ingestion.loader import Ledger
from app.ingestion.manifest import FolderResult, ManifestError, ingest_folder, read_departments
from app.kpi.loader import load_seed_definitions, load_seed_targets

SYNTHETIC_DOMAIN = "edss.test"  # the reserved domain of the synthetic personas


@dataclass
class RealLoad:
    outcome: FolderResult
    written: dict[str, int] = field(default_factory=dict)
    switched_to_real: bool = False
    personas_switched_off: int = 0


def _floors(conn) -> dict[str, int]:
    def top(table) -> int:
        return conn.execute(select(func.coalesce(func.max(table.c.id), 0))).scalar_one()

    return {
        "source": top(t.source_system), "batch": top(t.ingest_batch),
        "fact": top(t.metric_fact), "publication": top(t.research_publication),
    }  # fmt: skip


def _ledger(engine: Engine, folder: Path, today: date) -> tuple[Ledger, dict[str, int]]:
    manifest = yaml.safe_load((folder / "manifest.yml").read_text()) or {}
    departments = read_departments(folder / manifest.get("departments", "departments.csv"))
    with engine.connect() as conn:
        floors = _floors(conn)
        sources = [
            SourceSystem(id=r.id, name=r.name, owner_office=r.owner_office, kind=r.kind)
            for r in conn.execute(select(t.source_system).order_by(t.source_system.c.id))
        ]
        if real_data_present(conn):
            held, _, _ = load_dataset(conn, "real")
            batches, facts, publications = held.batches, held.facts, held.publications
        else:
            batches, facts, publications = (), (), ()
    ledger = Ledger.restored(
        departments, today, "real", sources=sources, batches=batches, facts=facts,
        publications=publications, floors=floors,
    )  # fmt: skip
    return ledger, floors


def load_real_folder(engine: Engine, folder: Path, today: date, ingested_by: str) -> RealLoad:
    """Read the folder and add what is new. Nothing is written if a file could not be read."""
    if not (folder / "manifest.yml").exists():
        raise ManifestError(f"{folder} has no manifest.yml")
    ledger, floors = _ledger(engine, folder, today)
    outcome = ingest_folder(folder, today, data_mode="real", ingested_by=ingested_by, ledger=ledger)
    load = RealLoad(outcome)
    if outcome.errors:
        return load

    held_sources = floors["source"]
    new_sources = [s for s in ledger.sources if s.id > held_sources]
    new_batches = [b for b in ledger.batches if b.id > floors["batch"]]
    new_facts = [f for f in ledger.facts if f.id > floors["fact"]]
    new_publications = [p for p in ledger.publications if p.id > floors["publication"]]
    with engine.begin() as conn:
        first = not real_data_present(conn)
        insert_records(conn, new_sources, new_batches, new_facts, new_publications)
        conn.execute(text("update department set real_position = null"))
        for position, d in enumerate(ledger.departments):
            conn.execute(
                text(
                    "insert into department (code, name, school, active, real_position) values "
                    "(:code, :name, :school, :active, :p) on conflict (code) do update set "
                    "name = :name, school = :school, active = :active, real_position = :p"
                ),
                {**d.model_dump(), "p": position},
            )
        if not conn.execute(select(func.count()).select_from(t.kpi_definition)).scalar_one():
            # the placeholder list, marked PLACEHOLDER_PENDING_IQAC, until IQAC supplies its own
            definitions = load_seed_definitions()
            conn.execute(
                insert(t.kpi_definition),
                [
                    {**d.model_dump(), "domain_tags": [x.value for x in d.domain_tags]}
                    for d in definitions
                ],
            )
            conn.execute(insert(t.kpi_target), [x.model_dump() for x in load_seed_targets()])
        for table in ("source_system", "ingest_batch", "metric_fact", "research_publication"):
            conn.execute(
                text(
                    f"select setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"coalesce((select max(id) from {table}), 0) + 1, false)"
                )
            )
        if first and new_batches:
            conn.execute(
                text(
                    "insert into system_config (key, value) values ('data_mode', 'real') "
                    "on conflict (key) do update set value = 'real'"
                )
            )
            load.personas_switched_off = conn.execute(
                text(
                    "update app_user set active = false, session_version = session_version + 1 "
                    "where email like :pattern and active"
                ),
                {"pattern": f"%@{SYNTHETIC_DOMAIN}"},
            ).rowcount
            load.switched_to_real = True

    load.written = {
        "batches": len(new_batches), "facts": len(new_facts), "publications": len(new_publications),
        "unchanged files": sum(1 for _, r in outcome.results if r.noop),
    }  # fmt: skip
    audit = DbAuditLog(engine)
    audit.append(
        actor_type="system", actor_id=ingested_by, action="data.load_real",
        inputs={"folder": folder.name, "departments": [d.code for d in ledger.departments]},
        outputs={**load.written, "rejected": outcome.rejected,
                 "non_final": sum(1 for f in new_facts if f.status is not FactStatus.FINAL)},
    )  # fmt: skip
    if load.switched_to_real:
        audit.append(
            actor_type="system", actor_id=ingested_by, action="data.mode_real",
            inputs={"folder": folder.name},
            outputs={"note": "The first real data was loaded. Synthetic records are archived and no "
                     "longer read. The synthetic personas were switched off.",
                     "personas_switched_off": load.personas_switched_off},
        )  # fmt: skip
    return load
