#!/usr/bin/env python3
"""
Runs Assignments 1-12, then the two bridge labs (13 specialists, 14 capstone)
from lab_kit/labs, stopping at the first failure. Each assignment's console
output is saved next to it as output/run_log.txt as evidence.

    python run_all.py
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def scripts():
    for folder in sorted(HERE.glob("Assignment-*")):
        yield from sorted(folder.glob("lab*.py"))
    yield from sorted((HERE / "lab_kit" / "labs").glob("lab*.py"))


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    env =dict(os.environ, PYTHONIOENCODING="utf-8")
    for path in scripts():
        print(f"\n{'#' * 78}\n# {path.relative_to(HERE)}\n{'#' * 78}", flush=True)
        result = subprocess.run([sys.executable, str(path)], env=env,
                                capture_output=True, text=True, encoding="utf-8")
        print(result.stdout, end="", flush=True)
        print(result.stderr, end="", file=sys.stderr, flush=True)
        log_dir = path.parent / "output"
        log_dir.mkdir(exist_ok=True)
        (log_dir / "run_log.txt").write_text(result.stdout + result.stderr, encoding="utf-8") \
            if path.parent.name.startswith("Assignment-") else None
        if result.returncode != 0:
            print(f"\nSTOPPED: {path.name} exited with code {result.returncode}")
            sys.exit(result.returncode)
    print("\nAll 12 assignments and the 2 bridge labs ran successfully.")


if __name__ == "__main__":
    main()
