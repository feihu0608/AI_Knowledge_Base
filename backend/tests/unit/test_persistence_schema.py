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


def test_department_closure_foreign_keys_have_unique_names():
    table = Base.metadata.tables["department_closure"]
    names = sorted(constraint.name for constraint in table.foreign_key_constraints)

    assert names == [
        "fk_department_closure_ancestor_department",
        "fk_department_closure_descendant_department",
    ]
