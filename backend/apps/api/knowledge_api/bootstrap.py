from __future__ import annotations

from knowledge_application.auth_service import AuthenticationService
from knowledge_application.chat_service import ChatApplicationService
from knowledge_application.config import Settings
from knowledge_application.ingestion_service import IngestionApplicationService
from knowledge_application.security import PasswordHasher, TokenService
from knowledge_application.storage import LocalObjectStorage
from knowledge_persistence import Base, Database, OutboxRepository, UserRepository
from knowledge_graphs.knowledge_answer import build_knowledge_answer_graph
from knowledge_graphs.knowledge_answer.mock_runtime import build_mock_answer_runtime
from knowledge_graphs.knowledge_answer.live_runtime import build_live_answer_runtime


def configure_services(app, settings: Settings, database: Database | None = None) -> None:
    db = database or Database(settings.database_url)
    if settings.auto_create_schema:
        import knowledge_persistence.models  # noqa: F401
        Base.metadata.create_all(db.engine)
    app.state.settings = settings
    app.state.database = db
    app.state.auth_service = AuthenticationService(
        UserRepository(), PasswordHasher(),
        TokenService(settings.jwt_secret, settings.jwt_algorithm, settings.access_token_minutes),
    )
    app.state.ingestion_service = IngestionApplicationService(
        LocalObjectStorage(settings.storage_dir), OutboxRepository(), provider_mode=settings.provider_mode
    )
    answer_runtime = (
        build_live_answer_runtime(settings, db) if settings.ai_mode == "live"
        else build_mock_answer_runtime()
    )
    app.state.chat_service = ChatApplicationService(
        build_knowledge_answer_graph(answer_runtime), provider_mode=settings.ai_mode
    )
