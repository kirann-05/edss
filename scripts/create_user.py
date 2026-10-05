"""make create-user: add a person to the database from the server's command line.

For the first real administrator, before real data is opened: the synthetic personas are switched
off when the first real data is loaded. The password is asked for twice and never shown, logged or
written anywhere but as its hash. The addition is a row in the audit log.

Run from backend:  uv run python ../scripts/create_user.py --email ... --name ... --role admin
"""

import argparse
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy import create_engine, func, select, text

from app.core.security import hash_password
from app.db import schema as t
from app.db.audit_store import DbAuditLog
from app.db.urls import owner_url
from app.domain.enums import Role
from app.domain.models import AppUser
from app.services.users import _EMAIL, MIN_PASSWORD


def refused(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", required=True, choices=[r.value for r in Role])
    parser.add_argument("--dept", help="the department of a HOD")
    parser.add_argument("--school", help="the school of a Dean")
    args = parser.parse_args()
    email = args.email.strip().lower()
    dept = args.dept.strip().upper() if args.dept else None
    if not _EMAIL.match(email):
        return refused("That is not an email address.")
    if email.endswith("@edss.test"):
        return refused("The .test domain is for synthetic personas only.")
    if not args.name.strip():
        return refused("A person needs a name.")
    try:  # the role's own rules, such as a HOD's department, before anyone types a password
        AppUser(
            id=0,
            email=email,
            name=args.name.strip(),
            role=Role(args.role),
            dept_code=dept,
            school=args.school,
        )
    except ValidationError as error:
        return refused(error.errors()[0]["msg"].removeprefix("Value error, ") + ".")

    engine = create_engine(owner_url())
    try:
        with engine.connect() as conn:
            if conn.execute(select(t.app_user.c.id).where(t.app_user.c.email == email)).first():
                return refused("Someone already has that email.")
            if (
                dept
                and not conn.execute(
                    select(t.department.c.code).where(t.department.c.code == dept)
                ).first()
            ):
                return refused(f"There is no department {dept!r}.")

        try:
            password = getpass.getpass("Password: ")
            if len(password) < MIN_PASSWORD:
                return refused(f"A password needs at least {MIN_PASSWORD} characters.")
            if getpass.getpass("Again: ") != password:
                return refused("The two did not match.")
        except (EOFError, KeyboardInterrupt):
            return refused("\nStopped: no password was given, so nobody was added.")

        with engine.begin() as conn:
            next_id = (
                conn.execute(select(func.coalesce(func.max(t.app_user.c.id), 0))).scalar_one() + 1
            )
            user = AppUser(
                id=next_id, email=email, name=args.name.strip(), role=Role(args.role),
                dept_code=dept, school=args.school,
            )  # fmt: skip
            conn.execute(
                text(
                    "insert into app_user (id, email, name, role, dept_code, school, active, "
                    "password_hash, session_version) values (:id, :email, :name, :role, :dept, "
                    ":school, true, :hash, 0)"
                ),
                {"id": user.id, "email": user.email, "name": user.name, "role": user.role.value,
                 "dept": user.dept_code, "school": user.school, "hash": hash_password(password)},
            )  # fmt: skip
        DbAuditLog(engine).append(
            actor_type="system", actor_id=f"create-user by {getpass.getuser()}", action="user.create",
            inputs={"email": user.email, "role": user.role.value}, outputs={"id": user.id},
        )  # fmt: skip
    finally:
        engine.dispose()
    print(f"{user.name} ({user.role.value}) can now sign in as {user.email}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
