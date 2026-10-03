"""Authorisation for every route (CHECKLIST D3).

The first test walks the real route table, so a route added later that forgets to check the
session fails here without anyone having to remember to write a test for it.
"""

import pytest

from .conftest import EMAILS  # noqa: F401  (keeps the personas importable for readers)

# routes that are meant to work without signing in
PUBLIC = {
    ("GET", "/api/health"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/auth/demo-users"),  # 404 unless demo mode is on
    ("POST", "/api/auth/demo-login"),  # 404 unless demo mode is on
    ("GET", "/api/docs"),  # development aid, synthetic mode only
    ("GET", "/api/openapi.json"),
}


def routes(app):
    """Every (method, path) the app serves, flattened.

    FastAPI wraps each included router lazily, so app.routes is not flat. This walks the
    wrappers. If a FastAPI upgrade changes them, the cross-check against the OpenAPI schema
    below fails, so the walk can never quietly stop covering routes.
    """

    def walk(items, prefix=""):
        for route in items:
            if type(route).__name__ == "_IncludedRouter":
                yield from walk(
                    route.original_router.routes, prefix + (route.include_context.prefix or "")
                )
            else:
                for method in getattr(route, "methods", None) or ():
                    if method not in {"HEAD", "OPTIONS"}:
                        yield method, prefix + route.path

    yield from walk(app.routes)


def fill(path: str) -> str:
    return path.replace("{key}", "PL_PCT").replace("{domain}", "academic")


def test_every_route_that_is_not_public_refuses_a_request_with_no_session(app, anonymous):
    protected = [(m, p) for m, p in routes(app) if (m, p) not in PUBLIC]
    assert protected, "found no protected routes, the route walk is broken"
    for method, path in protected:
        response = anonymous.request(method, fill(path), json={} if method != "GET" else None)
        assert response.status_code == 401, f"{method} {path} answered {response.status_code}"


def test_the_route_walk_sees_every_route_in_the_api_contract(app):
    walked = {(m, p) for m, p in routes(app)}
    for path, methods in app.openapi()["paths"].items():
        for method in methods:
            assert (method.upper(), path) in walked, (
                f"the route walk missed {method.upper()} {path}"
            )
    assert len(walked) >= 12, walked


def test_the_public_list_only_names_routes_that_exist(app):
    walked = {(m, p) for m, p in routes(app)}
    assert walked >= PUBLIC, PUBLIC - walked


DASHBOARD = ["/api/kpis", "/api/kpis/PL_PCT", "/api/domains/academic"]
HEALTH = ["/api/data-health"]

# role -> may it read the dashboard endpoints, may it read data health
ACCESS = {
    "registrar": (True, True),
    "principal": (True, True),
    "dean": (True, True),
    "hod_cse": (True, True),
    "viewer": (False, False),
    "admin": (False, True),
}


@pytest.mark.parametrize(("persona", "access"), ACCESS.items())
def test_each_role_gets_exactly_the_endpoints_its_permissions_allow(login, persona, access):
    client = login(persona)
    may_dashboard, may_health = access
    for path in DASHBOARD:
        assert client.get(path).status_code == (200 if may_dashboard else 403), (persona, path)
    for path in HEALTH:
        assert client.get(path).status_code == (200 if may_health else 403), (persona, path)


@pytest.mark.parametrize("persona", list(ACCESS))
def test_every_signed_in_role_can_read_system_status(login, persona):
    assert login(persona).get("/api/system/status").status_code == 200
