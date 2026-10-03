import secrets
from datetime import date

from fastapi import FastAPI

from app import __version__
from app.api.deps import AppState
from app.api.routes import auth, data_health, health, kpis, system
from app.core.config import Settings, get_settings
from app.core.tracing import enforce_no_external_tracing
from app.services.store import DataStore
from app.services.users import build_seed_users


def create_app(settings: Settings | None = None, today: date | None = None) -> FastAPI:
    settings = settings or get_settings()
    enforce_no_external_tracing()

    if settings.data_mode == "real":
        # Only the synthetic in-memory services exist so far. They must never stand in for real
        # data (CHECKLIST F3 builds the Postgres services this mode needs).
        raise RuntimeError("DATA_MODE=real needs the Postgres services, which are not built yet")

    jwt_secret = settings.jwt_secret.get_secret_value() if settings.jwt_secret else None
    if jwt_secret is None:
        # Synthetic mode only: a throwaway secret, so sessions end when the server restarts
        jwt_secret = secrets.token_urlsafe(32)

    seed_password = (
        settings.edss_seed_password.get_secret_value() if settings.edss_seed_password else None
    )
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
    app.state.edss = AppState(
        settings=settings,
        store=DataStore.build(today or date.today(), settings.stale_after_days),
        users=build_seed_users(seed_password),
        jwt_secret=jwt_secret,
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(system.router, prefix="/api")
    app.include_router(kpis.router, prefix="/api")
    app.include_router(data_health.router, prefix="/api")
    return app
