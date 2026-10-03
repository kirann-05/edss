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
    args = parser.parse_args()

    if args.mode == "real":
        # real data must never reach git (CLAUDE.md). Say so if this folder is not ignored
        ignored = (
            subprocess.run(
                ["git", "check-ignore", "-q", str(args.folder)], capture_output=True
            ).returncode
            == 0
        )
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
    return 1 if outcome.rejected else 0


if __name__ == "__main__":
    sys.exit(main())
