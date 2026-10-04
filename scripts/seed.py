"""Write the synthetic sample, read it back through the real ingestion path, and check it.

    uv run python ../scripts/seed.py            # from the backend folder, or: make seed

1. Generates the synthetic dataset for a fixed reference date, so the committed sample is the same
   every time. (The running app stamps its data relative to today instead, so a demo is always current.)
2. Writes it to data/sample as the CSV files an office would send, with a manifest.
3. Reads that folder back with the same code a real folder goes through.
4. Asserts the row counts match what was written and that every planted trap, T1 to T10, is there.

If a later change to the generator, the exporter or the validator loses a row or a trap, this fails
before anything built on the data can pass for the wrong reason.
"""

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

from app.ingestion.export import export_dataset, export_templates
from app.ingestion.manifest import ingest_folder
from app.kpi.loader import load_seed_definitions, load_seed_targets
from app.services.store import DataStore
from app.synthetic.generator import generate
from app.synthetic.traps import observe

REFERENCE = date(2026, 10, 1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=Path("../data/sample"))
    parser.add_argument(
        "--db",
        action="store_true",
        help="also replace the synthetic data in PostgreSQL with it, read it back and check again",
    )
    args = parser.parse_args()

    dataset = generate(reference_date=REFERENCE)
    if args.out.exists():
        shutil.rmtree(args.out)
    export_dataset(dataset, args.out)
    export_templates(args.out / "templates")
    print(
        f"Wrote the synthetic sample to {args.out} ({len(dataset.facts)} facts, {len(dataset.publications)} publications)"
    )

    outcome = ingest_folder(args.out, REFERENCE, data_mode="synthetic")
    ledger = outcome.ledger
    problems = []
    if outcome.errors:
        problems += outcome.errors
    if outcome.rejected:
        problems.append(f"{outcome.rejected} rows were rejected on the way back in")
    if len(ledger.facts) != len(dataset.facts):
        problems.append(f"{len(ledger.facts)} facts came back, {len(dataset.facts)} were written")
    if len(ledger.publications) != len(dataset.publications):
        problems.append(
            f"{len(ledger.publications)} publications came back, {len(dataset.publications)} were written"
        )
    print(
        f"Read it back: {len(ledger.facts)} facts, {len(ledger.publications)} publications, {outcome.rejected} rejected"
    )

    store = DataStore(ledger.dataset(), load_seed_definitions(), load_seed_targets(), REFERENCE, 90)
    print("\nPlanted traps, found again in the loaded data:")
    for trap in observe(store):
        print(f"  {'ok  ' if trap.ok else 'LOST'} {trap.id:3} {trap.what}: {trap.observed}")
        if not trap.ok:
            problems.append(f"trap {trap.id} was lost")

    if args.db and not problems:
        problems += into_database(ledger.dataset())
    if problems:
        print("\nSEED FAILED:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print("\nSeed passed.")
    return 0


def into_database(dataset) -> list[str]:
    from sqlalchemy import create_engine  # noqa: PLC0415  only --db needs the database

    from app.db.dataset_store import load_dataset, save_dataset  # noqa: PLC0415
    from app.db.urls import owner_url  # noqa: PLC0415

    engine = create_engine(owner_url())
    with engine.begin() as conn:
        save_dataset(conn, dataset, load_seed_definitions(), load_seed_targets())
    with engine.connect() as conn:
        back, definitions, targets = load_dataset(conn)
    engine.dispose()
    problems = (
        [] if back == dataset else ["what came back from the database differs from what went in"]
    )
    print(
        f"\nWrote it to PostgreSQL and read it back: {len(back.facts)} facts, {len(back.publications)} publications"
    )
    for trap in observe(DataStore(back, definitions, targets, REFERENCE, 90)):
        print(f"  {'ok  ' if trap.ok else 'LOST'} {trap.id:3} found in the database")
        if not trap.ok:
            problems.append(f"trap {trap.id} was lost in the database")
    return problems


if __name__ == "__main__":
    sys.exit(main())
