from pathlib import Path

from knowledge_application.security import PasswordHasher
from knowledge_persistence import Base, Database
from knowledge_persistence.models import (
    Chunk, Department, DepartmentClosure, Document, DocumentAclRow, DocumentVersion,
    KnowledgeBase, RolePermission, Tenant, User,
)
from knowledge_retrieval import AuthorizedMilvusRetriever


class Embedder:
    def embed(self, texts): return [[0.1, 0.2]]


class Reranker:
    def rerank(self, query, documents, *, top_n): return [(index, 0.9-index*0.1) for index in range(min(top_n, len(documents)))]


class VectorStore:
    def search(self, **kwargs):
        assert kwargs["tenant_id"] == "tenant-a"
        return [{"id": "allowed", "distance": 0.95}, {"id": "denied", "distance": 0.99}]


def test_local_retrieval_applies_database_acl_after_milvus(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path/'retrieval.db'}")
    Base.metadata.create_all(database.engine)
    with database.session_factory() as session:
        session.add_all([
            Tenant(id="tenant-a", name="A"), Department(tenant_id="tenant-a", id="dept", name="部门"),
            DepartmentClosure(tenant_id="tenant-a", ancestor_id="dept", descendant_id="dept", depth=0),
            User(tenant_id="tenant-a", id="alice", username="alice",
                 password_hash=PasswordHasher(iterations=1000).hash("long-password"), department_id="dept"),
            RolePermission(tenant_id="tenant-a", role_id="unused", permission_code="chat.use"),
            KnowledgeBase(tenant_id="tenant-a", id="kb", name="库"),
            Document(tenant_id="tenant-a", id="doc-a", knowledge_base_id="kb", title="可见", active_version_id="v-a"),
            Document(tenant_id="tenant-a", id="doc-b", knowledge_base_id="kb", title="不可见", active_version_id="v-b"),
            DocumentVersion(tenant_id="tenant-a", id="v-a", document_id="doc-a", source_filename="a.md",
                            source_sha256="a"*64, parser_version="p", chunker_version="c", index_version="idx", status="published"),
            DocumentVersion(tenant_id="tenant-a", id="v-b", document_id="doc-b", source_filename="b.md",
                            source_sha256="b"*64, parser_version="p", chunker_version="c", index_version="idx", status="published"),
            DocumentAclRow(tenant_id="tenant-a", document_id="doc-a", subject_type="user", subject_id="alice"),
            DocumentAclRow(tenant_id="tenant-a", document_id="doc-b", subject_type="user", subject_id="bob"),
            Chunk(tenant_id="tenant-a", id="allowed", document_id="doc-a", version_id="v-a", ordinal=0, text="允许"),
            Chunk(tenant_id="tenant-a", id="denied", document_id="doc-b", version_id="v-b", ordinal=0, text="禁止"),
        ])
        session.commit()
    # Add feature permission directly through a synthetic role assignment is covered by auth tests;
    # this retrieval assertion focuses on document ACL, so grant permission in the loaded identity via role rows.
    from knowledge_persistence.models import Role, UserRole
    with database.session_factory() as session:
        session.add_all([Role(tenant_id="tenant-a", id="unused", code="employee", name="员工"),
                         UserRole(tenant_id="tenant-a", user_id="alice", role_id="unused")])
        session.commit()
    retriever = AuthorizedMilvusRetriever(
        database=database, vector_store=VectorStore(), embedder=Embedder(), reranker=Reranker(), index_version="idx"
    )
    evidence = retriever.search(tenant_id="tenant-a", user_id="alice", query="制度")
    assert [item.evidence_id for item in evidence] == ["allowed"]
