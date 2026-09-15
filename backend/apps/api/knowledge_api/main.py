from __future__ import annotations

from fastapi import FastAPI
from redis import Redis
from sqlalchemy import text

from knowledge_application.config import Settings
from knowledge_persistence import Database
from knowledge_vector_store.milvus import MilvusVectorStore

from .bootstrap import configure_services
from .routes.auth import router as auth_router
from .routes.organization import router as organization_router
from .routes.knowledge import router as knowledge_router
from .routes.chat import router as chat_router
from .routes.operations import router as operations_router


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="AI Knowledge Base", version="0.1.0")
    configure_services(app, settings, database)
    app.include_router(auth_router)
    app.include_router(organization_router)
    app.include_router(knowledge_router)
    app.include_router(chat_router)
    app.include_router(operations_router)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/api/ready")
    def ready() -> dict:
        checks: dict[str, str] = {}
        try:
            with app.state.database.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
        try:
            client = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
            checks["redis"] = "ok" if client.ping() else "error"
            client.close()
        except Exception:
            checks["redis"] = "error"
        try:
            store = MilvusVectorStore(
                uri=settings.milvus_uri, token=settings.milvus_token or None,
                collection=settings.milvus_collection,
            )
            checks["milvus"] = "ok" if store.is_ready() else "missing_collection"
        except Exception:
            checks["milvus"] = "error"
        checks.update({
            "ai": "configured" if settings.ai_mode == "live" else settings.ai_mode,
            "mcp": "configured" if settings.mcp_mode == "live" else settings.mcp_mode,
            "parser": "configured" if settings.parser_mode == "live" else settings.parser_mode,
        })
        infrastructure_ok = all(checks[name] == "ok" for name in ("database", "redis", "milvus"))
        return {"status": "ready" if infrastructure_ok else "degraded", **checks}

    return app


app = create_app()
