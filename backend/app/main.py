from fastapi import FastAPI

from app import __version__
from app.api.routes import health
from app.core.tracing import enforce_no_external_tracing


def create_app() -> FastAPI:
    enforce_no_external_tracing()
    app = FastAPI(
        title="EDSS API",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.include_router(health.router, prefix="/api")
    return app
