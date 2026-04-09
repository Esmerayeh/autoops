import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from control_plane.app.api.router import api_router
from control_plane.app.core.config import settings
from control_plane.app.core.db import SessionLocal, init_db
from control_plane.app.core.logging import configure_logging
from control_plane.app.services.bootstrap_service import BootstrapService
from control_plane.app.web.routes import router as web_router


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    if settings.enable_bootstrap_admin and os.getenv("AUTOOPS_ENABLE_BOOTSTRAP_ON_STARTUP", "1") == "1":
        db = SessionLocal()
        try:
            BootstrapService(db).ensure_demo_tenant()
        finally:
            db.close()
    yield


def create_app(initialize_db: bool = True, enable_bootstrap: bool = True) -> FastAPI:
    """Create the AutoOps AI control-plane application."""
    configure_logging()
    if initialize_db:
        init_db()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=app_lifespan if enable_bootstrap else None,
    )
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/control-static", StaticFiles(directory=str(static_dir)), name="control-static")
    app.include_router(web_router)
    app.include_router(api_router, prefix="/api/v1")

    return app

_skip_startup_init = os.getenv("AUTOOPS_SKIP_STARTUP_INIT") == "1"
app = create_app(initialize_db=not _skip_startup_init, enable_bootstrap=not _skip_startup_init)
