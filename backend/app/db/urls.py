"""Where the database is, built from .env without ever printing the password.

The owner runs migrations. The app will connect as its own, narrower role (CHECKLIST L5e), so a
bug in the app cannot rewrite the audit log.
"""

import os
from pathlib import Path

from sqlalchemy.engine import URL

ENV = Path(__file__).resolve().parents[3] / ".env"


def env_value(name: str) -> str | None:
    if name in os.environ:
        return os.environ[name]
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return None


def owner_url(database: str | None = None) -> URL:
    password = env_value("EDSS_DB_PASSWORD")
    if not password:
        raise RuntimeError("EDSS_DB_PASSWORD is not set in .env (see .env.example)")
    return URL.create(
        "postgresql+psycopg",
        username="edss_owner",
        password=password,
        host="127.0.0.1",
        port=int(env_value("EDSS_DB_PORT") or 5432),
        database=database or env_value("EDSS_DB_NAME") or "edss",
    )
