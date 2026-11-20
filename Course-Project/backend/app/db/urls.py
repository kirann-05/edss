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


def _url(user: str, password_name: str, database: str | None) -> URL:
    password = env_value(password_name)
    if not password:
        raise RuntimeError(
            f"{password_name} is not set in .env (see .env.example, make db-migrate)"
        )
    return URL.create(
        "postgresql+psycopg",
        username=user,
        password=password,
        host=env_value("EDSS_DB_HOST") or "127.0.0.1",  # db inside compose
        port=int(env_value("EDSS_DB_PORT") or 5432),
        database=database or env_value("EDSS_DB_NAME") or "edss",
    )


def owner_url(database: str | None = None) -> URL:
    """The owner, who runs migrations and loads the synthetic data. Never the app."""
    return _url("edss_owner", "EDSS_DB_PASSWORD", database)


def app_url(database: str | None = None) -> URL:
    """The narrower role the app runs as: it cannot change or delete the audit log (L5e)."""
    return _url("edss_app", "EDSS_DB_APP_PASSWORD", database)
