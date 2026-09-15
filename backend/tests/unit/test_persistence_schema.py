from sqlalchemy import create_engine

from knowledge_persistence import Base
from knowledge_persistence import models  # noqa: F401


def test_all_foundation_tables_create_in_isolated_database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    expected = {
        "tenants", "departments", "department_closure", "users", "roles",
        "knowledge_bases", "documents", "document_versions", "chunks", "import_jobs",
        "graph_runs", "conversations", "messages", "answer_evidence", "model_calls",
        "faq_candidates", "faq_items", "knowledge_gaps", "outbox_events",
    }
    assert expected <= set(Base.metadata.tables)

