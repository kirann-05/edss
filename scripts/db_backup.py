"""make db-backup: a backup of the EDSS database into backups/, then proof that it restores.

The file is readable by this user only, and backups/ is never committed. A backup that has not
been restored is a hope, so this restores it into a throwaway database straight away, compares
every table with the live one, and verifies the audit chain. `--check FILE` checks an older one.

Run from backend:  uv run python ../scripts/db_backup.py
"""

import argparse
import sys
from pathlib import Path

from app.db.backup import check, dump


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", type=Path, help="check this backup instead of making a new one")
    args = parser.parse_args()
    path = args.check or dump()
    if not args.check:
        print(
            f"Backup written: {path} ({path.stat().st_size // 1024} KB, readable by this user only)"
        )
    report = check(path, compare_with=None if args.check else "edss")
    print(
        f"Restored into a throwaway database: {', '.join(f'{k} {v}' for k, v in report.rows.items())}"
    )
    for table, (live, restored) in report.differences.items():
        print(f"  DIFFERS {table}: {live} live, {restored} restored")
    print(
        f"Audit chain: {'verifies' if report.chain_ok else 'BROKEN'} over {report.chain_checked} rows"
        + (f" ({report.chain_reason})" if report.chain_reason else "")
    )
    print("Backup is good." if report.ok else "BACKUP FAILED ITS CHECK.")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
