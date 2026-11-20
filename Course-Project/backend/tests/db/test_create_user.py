"""make create-user: how the university's first administrator is added, from the command line."""

import importlib.util
import secrets
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.security import verify_password
from app.db.urls import owner_url
from tests.database_fixtures import ALEMBIC_INI, _admin

pytestmark = pytest.mark.db
SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "create_user.py"
PASSWORD = "a-long-admin-password"


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("create_user", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def db(scratch_db):
    """A database of its own, with only the migrations, as a new server has it."""
    name = f"edss_users_{secrets.token_hex(4)}"
    with _admin() as admin:
        admin.execute(f'create database "{name}"')
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("EDSS_DB_NAME", name)
        command.upgrade(Config(ALEMBIC_INI), "head")
        engine = create_engine(owner_url(database=name))
        yield engine
        engine.dispose()
    with _admin() as admin:
        admin.execute(f'drop database "{name}" with (force)')


@pytest.fixture
def run(script, db, monkeypatch, capsys):
    """Run the script with these arguments, typing these passwords at its prompts."""

    def go(*args, typed=(PASSWORD, PASSWORD)):
        monkeypatch.setenv("EDSS_DB_NAME", db.url.database)
        monkeypatch.setattr(sys, "argv", ["create_user.py", *args])
        answers = iter(typed)
        asked = []

        def prompt(label):
            asked.append(label)
            return next(answers)

        monkeypatch.setattr(script.getpass, "getpass", prompt)
        code = script.main()
        out = capsys.readouterr()
        return code, out.out + out.err, asked

    return go


def people(db, email):
    with db.connect() as conn:
        return conn.execute(
            text("select name, role, active, password_hash from app_user where email = :e"),
            {"e": email},
        ).all()


def test_an_administrator_is_added_with_only_a_hash_of_the_password_and_an_audit_row(run, db):
    code, said, asked = run(
        "--email", "IT.Admin@Uni.example", "--name", " IT Admin ", "--role", "admin"
    )
    assert code == 0 and "can now sign in as it.admin@uni.example" in said
    assert asked == ["Password: ", "Again: "]
    [(name, role, active, stored)] = people(db, "it.admin@uni.example")
    assert (name, role, active) == ("IT Admin", "admin", True)
    assert stored != PASSWORD and verify_password(stored, PASSWORD)
    with db.connect() as conn:
        row = conn.execute(
            text("select inputs, outputs from audit_log where action = 'user.create'")
        ).one()
    assert row.inputs == {"email": "it.admin@uni.example", "role": "admin"}
    assert PASSWORD not in str(row)


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (["--email", "not-an-email", "--name", "X", "--role", "admin"], "not an email address"),
        (["--email", "a@edss.test", "--name", "X", "--role", "admin"], "synthetic personas only"),
        (["--email", "a@uni.example", "--name", "  ", "--role", "admin"], "needs a name"),
        (["--email", "a@uni.example", "--name", "X", "--role", "hod"], "must have a department"),
        (["--email", "a@uni.example", "--name", "X", "--role", "hod", "--dept", "NOPE"], "no department 'NOPE'"),
    ],
)  # fmt: skip
def test_a_wrong_request_is_refused_before_any_password_is_asked(run, db, args, reason):
    code, said, asked = run(*args)
    assert code == 2 and reason in said and asked == []
    assert people(db, "a@uni.example") == []


def test_the_same_email_twice_is_refused(run):
    assert run("--email", "dup@uni.example", "--name", "One", "--role", "registrar")[0] == 0
    code, said, asked = run("--email", "dup@uni.example", "--name", "Two", "--role", "registrar")
    assert code == 2 and "already has that email" in said and asked == []


@pytest.mark.parametrize(
    ("typed", "reason"),
    [((PASSWORD, "something-else-entirely"), "did not match"), (("short",), "at least")],
)
def test_a_bad_password_adds_nobody(run, db, typed, reason):
    code, said, _ = run("--email", "pw@uni.example", "--name", "P", "--role", "viewer", typed=typed)
    assert code == 2 and reason in said
    assert people(db, "pw@uni.example") == []
