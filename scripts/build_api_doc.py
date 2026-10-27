"""Write docs/technical/05-api.md from the running app's own routes, so it cannot drift from the code.

For each endpoint: method, path, what it does (the route's docstring or summary), and who may call it, read
from the permission its dependencies require and mapped to roles through app/core/rbac.py.

Run from backend:  uv run python ../scripts/build_api_doc.py
"""

import inspect
from pathlib import Path

from fastapi.routing import APIRoute

from app.core.rbac import PERMISSIONS, Permission
from app.main import create_app

OUT = Path(__file__).resolve().parents[1] / "docs" / "technical" / "05-api.md"
ROLE_NAME = {
    "registrar": "Registrar", "principal": "Principal", "dean": "Dean", "hod": "HOD",
    "viewer": "Council", "admin": "Admin",
}  # fmt: skip


def permissions_of(route: APIRoute) -> tuple[set[Permission], bool]:
    """The permissions a route requires, and whether it needs someone signed in at all."""
    found: set[Permission] = set()
    signed_in = False
    stack = list(route.dependant.dependencies)
    while stack:
        dep = stack.pop()
        call = dep.call
        name = getattr(call, "__qualname__", "")
        if name == "current_user":
            signed_in = True
        if name.startswith("require.") and call.__closure__:
            for cell in call.__closure__:
                if isinstance(cell.cell_contents, Permission):
                    found.add(cell.cell_contents)
                    signed_in = True
        stack.extend(dep.dependencies)
    return found, signed_in


def who(route: APIRoute) -> str:
    perms, signed_in = permissions_of(route)
    if perms:
        roles = [ROLE_NAME[r.value] for r, held in PERMISSIONS.items() if perms <= held]
        return f"{', '.join(roles)} (`{', '.join(sorted(p.value for p in perms))}`)"
    return "Anyone signed in" if signed_in else "Public"


def walk(routes, prefix: str = ""):
    """Every endpoint with its full path. This FastAPI keeps an included router as a wrapper
    (original_router plus the prefix it was included with), so walk into those."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield prefix + route.path, route
        elif hasattr(route, "original_router"):
            yield from walk(route.original_router.routes, prefix + route.include_context.prefix)


def main() -> None:
    app = create_app()
    rows = []
    for path, route in walk(app.routes):
        if not path.startswith("/api"):
            continue
        doc = (
            inspect.getdoc(route.endpoint)
            or route.summary
            or route.name.replace("_", " ").capitalize()
        )
        first = doc.strip().splitlines()[0]
        for method in sorted(route.methods - {"HEAD"}):
            tag = (route.tags or ["other"])[0]
            rows.append((tag, path, method, first, who(route)))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))

    lines = [
        "# API reference",
        "",
        "Generated from the app's own routes by `scripts/build_api_doc.py` (run `make tech-docs`); do not edit by hand.",
        "Every path is under `/api` on the web app's origin. Sign-in is an HttpOnly session cookie. A missing session",
        "answers 401, a missing permission 403. Roles come from `backend/app/core/rbac.py`; a HOD or Dean also only ever",
        "sees their own department's or school's detail, whatever the endpoint. The machine-readable contract is",
        "`backend/openapi.json`, and the MCP connector's tools are listed in `03-architecture.md`.",
        "",
        f"{len(rows)} operations.",
        "",
    ]
    current = None
    for tag, path, method, what, roles in rows:
        if tag != current:
            lines += [
                "",
                f"## {tag.capitalize()}",
                "",
                "| Method | Path | What it does | Who may call it |",
                "| --- | --- | --- | --- |",
            ]
            current = tag
        lines.append(f"| {method} | `{path}` | {what} | {roles} |")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT} ({len(rows)} operations)")


if __name__ == "__main__":
    main()
