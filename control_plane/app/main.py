from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from control_plane.app.api.router import api_router
from control_plane.app.core.config import settings
from control_plane.app.core.db import SessionLocal, init_db
from control_plane.app.core.logging import configure_logging
from control_plane.app.services.bootstrap_service import BootstrapService
from control_plane.app.web.routes import router as web_router


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
    )
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/control-static", StaticFiles(directory=str(static_dir)), name="control-static")
    app.include_router(web_router)
    app.include_router(api_router, prefix="/api/v1")

    @app.on_event("startup")
    def bootstrap_demo_tenant() -> None:
        if not enable_bootstrap or not settings.enable_bootstrap_admin:
            return
        db = SessionLocal()
        try:
            BootstrapService(db).ensure_demo_tenant()
        finally:
            db.close()

    return app


app = create_app()
