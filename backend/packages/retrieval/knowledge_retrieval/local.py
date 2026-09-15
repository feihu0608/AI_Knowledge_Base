from __future__ import annotations

from sqlalchemy import select

from knowledge_domain.authorization.models import AccessContext, DocumentAcl, DocumentRecord
from knowledge_domain.authorization.service import AuthorizationService
from knowledge_graphs.knowledge_answer.runtime import Evidence
from knowledge_persistence.models import Chunk, Document, DocumentAclRow
from knowledge_persistence.repositories import UserRepository


class AuthorizedMilvusRetriever:
    def __init__(self, *, database, vector_store, embedder, reranker,
                 index_version: str, candidate_limit: int = 30, top_n: int = 8) -> None:
        self.database = database
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = reranker
        self.index_version = index_version
        self.candidate_limit = candidate_limit
        self.top_n = top_n
        self.users = UserRepository()
        self.authorization = AuthorizationService()

    def search(self, *, tenant_id: str, user_id: str, query: str) -> list[Evidence]:
        vector = self.embedder.embed([query])[0]
        hits = self.vector_store.search(
            tenant_id=tenant_id, index_version=self.index_version,
            embedding=vector, limit=self.candidate_limit,
        )
        hit_by_id = {str(hit.get("id")): hit for hit in hits if hit.get("id") is not None}
        if not hit_by_id:
            return []
        with self.database.session_factory() as session:
            identity = self.users.get_identity(session, tenant_id=tenant_id, user_id=user_id)
            if identity is None or not identity.user.active:
                return []
            context = AccessContext(
                tenant_id=tenant_id, user_id=user_id, department_id=identity.user.department_id,
                ancestor_department_ids=frozenset(identity.ancestor_department_ids),
                role_ids=frozenset(identity.role_ids), feature_permissions=frozenset(identity.permissions),
                authz_version=identity.user.authz_version, active=True,
            )
            chunks = session.scalars(select(Chunk).where(
                Chunk.tenant_id == tenant_id, Chunk.id.in_(hit_by_id)
            )).all()
            candidates: list[tuple[Chunk, Document, float]] = []
            for chunk in chunks:
                document = session.get(Document, (tenant_id, chunk.document_id))
                if document is None or document.active_version_id != chunk.version_id:
                    continue
                acl_rows = session.scalars(select(DocumentAclRow).where(
                    DocumentAclRow.tenant_id == tenant_id, DocumentAclRow.document_id == document.id
                )).all()
                acl = DocumentAcl(
                    global_visible=any(row.subject_type == "global" for row in acl_rows),
                    department_ids=frozenset(row.subject_id for row in acl_rows if row.subject_type == "department"),
                    role_ids=frozenset(row.subject_id for row in acl_rows if row.subject_type == "role"),
                    user_ids=frozenset(row.subject_id for row in acl_rows if row.subject_type == "user"),
                )
                record = DocumentRecord(
                    tenant_id=tenant_id, document_id=document.id, enabled=document.enabled,
                    active_version_id=document.active_version_id, acl_version=document.acl_version, acl=acl,
                )
                if self.authorization.can_read(context, record, required_feature="chat.use").allowed:
                    raw_score = float(hit_by_id[chunk.id].get("distance", 0.0))
                    candidates.append((chunk, document, max(0.0, min(raw_score, 1.0))))
            reranked = self.reranker.rerank(query, [item[0].text for item in candidates], top_n=self.top_n)
            return [Evidence(
                evidence_id=candidates[index][0].id, source_type="local", title=candidates[index][1].title,
                excerpt=candidates[index][0].text, score=max(0.0, min(score, 1.0)), tenant_id=tenant_id,
                source_id=candidates[index][1].id, source_version=candidates[index][0].version_id,
                acl_version=candidates[index][1].acl_version, acl_allowed=True,
            ) for index, score in reranked if 0 <= index < len(candidates)]
