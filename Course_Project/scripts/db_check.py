"""make db-check: can this machine reach its EDSS database, and does it have pgvector?

Reads EDSS_DB_PASSWORD (and EDSS_DB_PORT if set) from .env, connects to 127.0.0.1 as the owner,
and prints the server version and whether the vector extension is available. Never prints the
password.

Run from backend:  uv run python ../scripts/db_check.py
"""

import os
import sys
from pathlib import Path

import psycopg

ENV = Path(__file__).resolve().parent.parent / ".env"


def env_value(name: str) -> str | None:
    if name in os.environ:
        return os.environ[name]
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return None


def main() -> int:
    password = env_value("EDSS_DB_PASSWORD")
    if not password:
        print("EDSS_DB_PASSWORD is not set in .env")
        return 1
    port = int(env_value("EDSS_DB_PORT") or 5432)
    try:
        with psycopg.connect(
            host="127.0.0.1", port=port, dbname="edss", user="edss_owner", password=password,
            connect_timeout=5,
        ) as conn:  # fmt: skip
            version = conn.execute("show server_version").fetchone()[0]
            vector = conn.execute(
                "select default_version from pg_available_extensions where name = 'vector'"
            ).fetchone()
    except psycopg.OperationalError as error:
        print(f"Could not connect to 127.0.0.1:{port}. Is it running? make db-up\n  {error}")
        return 1
    print(f"PostgreSQL {version} on 127.0.0.1:{port}, database edss")
    print(f"pgvector available: {vector[0] if vector else 'no'}")
    return 0 if vector else 1


if __name__ == "__main__":
    sys.exit(main())
