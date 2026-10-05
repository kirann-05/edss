import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import date
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app import __version__
from app.agents.llm import LLMOutputError, LLMUnavailable
from app.api.routes import (
    admin,
    audit,
    auth,
    briefs,
    data_health,
    demo,
    health,
    kpis,
    reports,
    runs,
    system,
)
from app.bootstrap import build_state
from app.core.config import Settings, get_settings
from app.core.tracing import enforce_no_external_tracing
from app.governance.service import EditRejected, GovernanceError, PermissionDenied
from app.mcp_connector.server import build_server
from app.mcp_connector.tokens import RunTokens
from app.services.demo_state import seed_demo_state
from app.services.runs import RunError, RunNotFound
from app.services.store import DataStore


def create_app(
    settings: Settings | None = None,
    today: date | None = None,
    synchronous_runs: bool = False,
    store: DataStore | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    enforce_no_external_tracing()

    if settings.data_mode == "real" and not settings.edss_database:
        # the in-memory services must never stand in for real data: it lives in PostgreSQL only
        raise RuntimeError("DATA_MODE=real keeps the data in PostgreSQL: set EDSS_DATABASE=true")

    # API docs describe every endpoint, so they are a development aid only. No public docs, no
    # ReDoc and no OAuth redirect page, which nothing here uses.
    docs = settings.data_mode == "synthetic"
    tokens = RunTokens() if settings.connector_url else None
    mcp: Any = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            if mcp is None:
                yield
            else:
                async with mcp.session_manager.run():
                    yield
        finally:
            app.state.edss.close()  # the database connections, in database mode

    app = FastAPI(
        lifespan=lifespan,
        title="EDSS API",
        version=__version__,
        docs_url="/api/docs" if docs else None,
        openapi_url="/api/openapi.json" if docs else None,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )

    def fresh_state():
        state = build_state(
            settings,
            today or date.today(),
            synchronous_runs=synchronous_runs,
            store=store,
            # a fixed day in tests, the real day otherwise, so a refresh judges freshness by today
            clock=(lambda: today) if today else None,
            run_tokens=tokens,
        )
        # a database that already holds runs keeps them: the ready-made state is seeded once
        if state.demo_login_enabled and settings.edss_demo_state and not state.runs.runs():
            seed_demo_state(state)
        return state

    app.state.edss_factory = fresh_state  # the demo reset builds a new state the same way
    app.state.edss = fresh_state()

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(system.router, prefix="/api")
    app.include_router(kpis.router, prefix="/api")
    app.include_router(data_health.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")
    app.include_router(briefs.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(audit.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(demo.router, prefix="/api")
    if tokens is not None:
        # the connector's MCP endpoint (decision D29). It serves whatever state the app holds now,
        # so a demo reset or a data refresh reaches it at once
        parts = urlsplit(settings.connector_url)
        mcp = build_server(
            Live(lambda: app.state.edss.connector),
            audit=Live(lambda: app.state.edss.audit),
            tokens=tokens,
            public_url=f"{parts.scheme}://{parts.netloc}",
        )
        app.mount("/mcp", mcp.streamable_http_app(streamable_http_path="/"))
    if settings.edss_database:
        guard_data_mode(app)
    register_error_handlers(app)
    return app


def guard_data_mode(app: FastAPI) -> None:
    """In database mode, the stored data mode can change under a running app: loading real data
    switches it. A process that started in another mode still holds that mode's people and data in
    memory, so from that moment it answers nothing but a plain 503 until it is restarted (rule 7).
    The stored mode is read at most once a second."""
    checked = {"at": 0.0, "mode": None}

    @app.middleware("http")
    async def same_mode_as_at_start(request: Request, call_next):
        state = request.app.state.edss
        now = time.monotonic()
        if now - checked["at"] > 1.0:
            checked["mode"] = await run_in_threadpool(state.system_config.data_mode)
            checked["at"] = now
        if checked["mode"] != state.settings.data_mode:
            return JSONResponse(
                {
                    "detail": f"The database is now in {checked['mode']} mode, but this app started in "
                    f"{state.settings.data_mode} mode. Restart it with DATA_MODE={checked['mode']}."
                },
                status_code=503,
            )
        return await call_next(request)


class Live:
    """Whatever `get` returns at the moment of each call."""

    def __init__(self, get: Callable[[], Any]) -> None:
        self._get = get

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)


def register_error_handlers(app: FastAPI) -> None:
    """One consistent meaning for each kind of refusal, so the UI can show the right thing."""

    @app.exception_handler(PermissionDenied)
    async def refused(request: Request, error: PermissionDenied) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=403)

    @app.exception_handler(EditRejected)
    async def edit_rejected(request: Request, error: EditRejected) -> JSONResponse:
        # an edit that broke validation carries the report, so the person sees exactly what to fix
        assert error.report is not None
        body = {"detail": {"message": str(error), "report": error.report.model_dump(mode="json")}}
        return JSONResponse(body, status_code=422)

    @app.exception_handler(GovernanceError)
    async def governance_error(request: Request, error: GovernanceError) -> JSONResponse:
        # a rule that does not allow it right now: the state of the brief, not a malformed request
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.exception_handler(LLMUnavailable)
    async def model_down(request: Request, error: LLMUnavailable) -> JSONResponse:
        # the model server is not there: not the person's fault, and they can be told what to do
        return JSONResponse({"detail": str(error)}, status_code=503)

    @app.exception_handler(LLMOutputError)
    async def model_confused(request: Request, error: LLMOutputError) -> JSONResponse:
        return JSONResponse(
            {
                "detail": "The language model could not give a usable answer. Try again, or say it differently."
            },
            status_code=502,
        )

    @app.exception_handler(RunNotFound)
    async def no_run(request: Request, error: RunNotFound) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=404)

    @app.exception_handler(RunError)
    async def run_error(request: Request, error: RunError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=409)
