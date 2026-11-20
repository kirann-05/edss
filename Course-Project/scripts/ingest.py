"""Check a folder of exports and print the reconciliation report.

    uv run python ../scripts/ingest.py ../data/real/2026-10 --mode real --report ../data/real/2026-10/REPORT.md

Run it from the backend folder. It reads the folder's manifest.yml and every file it names, refuses
what breaks the data contract with a plain reason beside each row, and shows where there is no record
at all. Nothing is changed or filled in. It is what a data owner is shown to confirm their extract.

Exit code: 0 when everything was accepted, 1 when some rows were refused, 2 when a file or the
manifest could not be read at all.
"""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from app.ingestion.manifest import ManifestError, ingest_folder
from app.ingestion.reconcile import reconciliation_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("folder", type=Path)
    parser.add_argument("--mode", choices=["synthetic", "real"], default="real")
    parser.add_argument("--report", type=Path, help="write the report to this file as well")
    parser.add_argument(
        "--db", action="store_true",
        help="real data only: after the report, add what is new to PostgreSQL. The first real load "
        "switches the database to real mode (docs/RUNBOOK.md, Real data)",
    )  # fmt: skip
    args = parser.parse_args()

    if args.mode == "real":
        # real data must never reach git (CLAUDE.md). Say so if this folder is not ignored
        try:
            ignored = (
                subprocess.run(
                    ["git", "check-ignore", "-q", str(args.folder)], capture_output=True
                ).returncode
                == 0
            )
        except FileNotFoundError:  # no git here, as inside the container: nothing to warn about
            ignored = True
        if not ignored:
            print(
                f"WARNING: {args.folder} is not ignored by git. Real data belongs under data/real/.",
                file=sys.stderr,
            )

    try:
        outcome = ingest_folder(args.folder, date.today(), data_mode=args.mode)
    except ManifestError as error:
        print(f"Cannot read {args.folder}: {error}", file=sys.stderr)
        return 2

    report = reconciliation_report(outcome, str(args.folder))
    print(report)
    if args.report:
        args.report.write_text(report)
        print(f"Report written to {args.report}", file=sys.stderr)
    if outcome.errors:
        return 2
    if args.db:
        if args.mode != "real":
            print(
                "--db is for real data. Synthetic data goes in with make seed-db.", file=sys.stderr
            )
            return 2
        return into_database(args.folder)
    return 1 if outcome.rejected else 0


def into_database(folder: Path) -> int:
    import getpass  # noqa: PLC0415

    from sqlalchemy import create_engine  # noqa: PLC0415  only --db needs the database

    from app.db.real_data import load_real_folder  # noqa: PLC0415
    from app.db.urls import owner_url  # noqa: PLC0415

    engine = create_engine(owner_url())
    try:
        load = load_real_folder(engine, folder, date.today(), f"ingest by {getpass.getuser()}")
    finally:
        engine.dispose()
    if load.outcome.errors:
        print(
            "Nothing was written: a file could not be read (see the report above).", file=sys.stderr
        )
        return 2
    written = ", ".join(f"{v} {k}" for k, v in load.written.items())
    print(
        f"\nAdded to the database: {written}. Refused rows were not added: fix them at the source and load again."
    )
    if load.switched_to_real:
        print(
            "\nThe database is now in REAL mode. Synthetic records are archived and no longer read, and "
            f"{load.personas_switched_off} synthetic personas were switched off. Start the app with "
            "DATA_MODE=real, after creating an administrator: make create-user."
        )
    return 1 if load.outcome.rejected else 0


if __name__ == "__main__":
    sys.exit(main())
