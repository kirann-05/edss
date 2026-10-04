"""Give the app's database role its password and let it sign in (part of make db-migrate).

The password is EDSS_DB_APP_PASSWORD in .env. If it is not there yet, a long random one is
generated and written there. It is never printed. Run after the migrations, which create the
role with no way to sign in.

Run from backend:  uv run python ../scripts/db_roles.py
"""

import secrets
import sys

import psycopg
from psycopg import sql

from app.db.urls import ENV, env_value, owner_url


def main() -> int:
    password = env_value("EDSS_DB_APP_PASSWORD")
    if not password:
        password = secrets.token_urlsafe(24)
        text = ENV.read_text() if ENV.exists() else ""
        ENV.write_text(
            text
            + ("" if text.endswith("\n") or not text else "\n")
            + f"EDSS_DB_APP_PASSWORD={password}\n"
        )
        print("Added EDSS_DB_APP_PASSWORD to .env (value not shown)")
    url = owner_url()
    with psycopg.connect(
        host=url.host, port=url.port, dbname=url.database, user=url.username, password=url.password,
        autocommit=True,
    ) as conn:  # fmt: skip
        conn.execute(
            sql.SQL("alter role edss_app with login password {}").format(sql.Literal(password))
        )
    print("The app role edss_app can sign in. It cannot change or delete the audit log.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
