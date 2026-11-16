"""LangGraph's checkpoints in PostgreSQL, so a run survives a server restart (CHECKLIST L5g).

LangGraph's own Postgres checkpointer, over a small pool of connections as the app role. Its tables
belong to the library and are created by the library's `setup()`, which `make db-migrate` runs as
the owner; migration 0004's default privileges then let the app role use them. Our Alembic
migrations leave those tables alone (`app/db/schema.py`, `ours`).
"""

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from sqlalchemy.engine import URL


def conninfo(url: URL) -> str:
    """The libpq connection string psycopg wants, from a SQLAlchemy URL. Holds the password."""
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


def checkpointer(url: URL, max_size: int = 8) -> PostgresSaver:
    pool = ConnectionPool(
        conninfo(url),
        min_size=1,
        max_size=max_size,  # the four domain agents and option drafts write checkpoints at once
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )
    return PostgresSaver(pool)


def setup(url: URL) -> None:
    """Create or upgrade the checkpoint tables. Run as the owner, never by the app."""
    with PostgresSaver.from_conn_string(conninfo(url)) as saver:
        saver.setup()
