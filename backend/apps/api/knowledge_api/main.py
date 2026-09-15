from __future__ import annotations

from fastapi import FastAPI

from knowledge_application.config import Settings
from knowledge_persistence import Database

from .bootstrap import configure_services
from .routes.auth import router as auth_router
from .routes.organization import router as organization_router
from .routes.knowledge import router as knowledge_router
from .routes.chat import router as chat_router


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="AI Knowledge Base", version="0.1.0")
    configure_services(app, settings, database)
    app.include_router(auth_router)
    app.include_router(organization_router)
    app.include_router(knowledge_router)
    app.include_router(chat_router)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/ready")
    def ready() -> dict:
        return {
            "status": "degraded",
            "database": "not_configured",
            "redis": "not_configured",
            "milvus": "not_configured",
            "provider_mode": settings.provider_mode,
        }

    return app


app = create_app()
