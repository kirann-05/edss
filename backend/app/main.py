from datetime import date

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routes import (
    admin,
    audit,
    auth,
    briefs,
    data_health,
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
from app.services.runs import RunError, RunNotFound


def create_app(
    settings: Settings | None = None, today: date | None = None, synchronous_runs: bool = False
) -> FastAPI:
    settings = settings or get_settings()
    enforce_no_external_tracing()

    if settings.data_mode == "real":
        # Only the synthetic in-memory services exist so far. They must never stand in for real
        # data (CHECKLIST F3 builds the Postgres services this mode needs).
        raise RuntimeError("DATA_MODE=real needs the Postgres services, which are not built yet")

    # API docs describe every endpoint, so they are a development aid only. No public docs, no
    # ReDoc and no OAuth redirect page, which nothing here uses.
    docs = settings.data_mode == "synthetic"
    app = FastAPI(
        title="EDSS API",
        version=__version__,
        docs_url="/api/docs" if docs else None,
        openapi_url="/api/openapi.json" if docs else None,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )
    app.state.edss = build_state(settings, today or date.today(), synchronous_runs=synchronous_runs)

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
    register_error_handlers(app)
    return app


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

    @app.exception_handler(RunNotFound)
    async def no_run(request: Request, error: RunNotFound) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=404)

    @app.exception_handler(RunError)
    async def run_error(request: Request, error: RunError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=409)
