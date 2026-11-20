"""People, the Registrar's grants and the data mode, kept in PostgreSQL (CHECKLIST L5d).

The services keep their rules (app/services/users.py, connector.py, system_config.py); these
classes only load what they hold and write each change through. The data mode is the exception:
it is read from the table on every call, never cached, so rule 7 is checked against the database
itself and a change there takes effect at once.
"""

from sqlalchemy import Engine, delete, insert, select, text

from app.agents.connector import ScopeGrant
from app.db import schema as t
from app.domain.enums import Domain, Role
from app.domain.models import AppUser
from app.services.system_config import DataMode


class DbSystemConfig:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        with engine.begin() as conn:
            # a first start always records synthetic. Only loading real data switches a database
            # to real (app/db/real_data.py), so an env setting can never declare data real
            conn.execute(
                text(
                    "insert into system_config (key, value) values ('data_mode', 'synthetic') "
                    "on conflict do nothing"
                )
            )

    def data_mode(self) -> DataMode:
        with self._engine.connect() as conn:
            value = conn.execute(
                select(t.system_config.c.value).where(t.system_config.c.key == "data_mode")
            ).scalar_one()
        if value not in ("synthetic", "real"):
            return "real"  # anything unexpected is treated as the stricter mode
        return value  # type: ignore[return-value]

    def set_data_mode(self, mode: DataMode) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("update system_config set value = :v where key = 'data_mode'"), {"v": mode}
            )


class UserRows:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(self) -> tuple[tuple[AppUser, ...], dict[int, str], dict[int, int]]:
        with self._engine.connect() as conn:
            rows = conn.execute(select(t.app_user).order_by(t.app_user.c.id)).all()
        users = tuple(
            AppUser(
                id=r.id, email=r.email, name=r.name, role=Role(r.role), dept_code=r.dept_code,
                school=r.school, active=r.active,
            )
            for r in rows
        )  # fmt: skip
        return users, {r.id: r.password_hash for r in rows}, {r.id: r.session_version for r in rows}

    def save(self, user: AppUser, password_hash: str, session_version: int) -> None:
        values = {
            "id": user.id, "email": user.email, "name": user.name, "role": user.role.value,
            "dept_code": user.dept_code, "school": user.school, "active": user.active,
            "password_hash": password_hash, "session_version": session_version,
        }  # fmt: skip
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "insert into app_user (id, email, name, role, dept_code, school, active, "
                    "password_hash, session_version) overriding system value values (:id, :email, "
                    ":name, :role, :dept_code, :school, :active, :password_hash, :session_version) "
                    "on conflict (id) do update set email = :email, name = :name, role = :role, "
                    "dept_code = :dept_code, school = :school, active = :active, "
                    "password_hash = :password_hash, session_version = :session_version"
                ),
                values,
            )


class ScopeRows:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def load(self) -> list[ScopeGrant]:
        with self._engine.connect() as conn:
            rows = conn.execute(select(t.scope_grant).order_by(t.scope_grant.c.id)).all()
        return [
            ScopeGrant(
                Domain(r.domain), r.dept_code, r.granted_by, r.granted_on, r.expires_on, r.active
            )
            for r in rows
        ]

    def replace(self, grants: list[ScopeGrant]) -> None:
        with self._engine.begin() as conn:
            conn.execute(delete(t.scope_grant))
            if grants:
                conn.execute(
                    insert(t.scope_grant),
                    [{**g.__dict__, "domain": g.domain.value} for g in grants],
                )
