from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from .contracts import VectorRecord


class MilvusVectorStore:
    """Tenant-scoped Milvus adapter with injectable client for isolated tests."""

    def __init__(
        self,
        *,
        uri: str,
        token: str | None,
        collection: str,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        if client_factory is None:
            from pymilvus import MilvusClient

            client_factory = MilvusClient
        self._client = client_factory(uri=uri, token=token)
        self._collection = collection

    def ensure_collection(self, *, dimension: int) -> None:
        if not self._client.has_collection(collection_name=self._collection):
            self._client.create_collection(
                collection_name=self._collection, dimension=dimension,
                primary_field_name="id", id_type="string", max_length=64,
                vector_field_name="embedding", metric_type="COSINE",
                consistency_level="Strong", enable_dynamic_field=True,
            )

    def upsert(self, records: Sequence[VectorRecord]) -> int:
        if not records:
            return 0
        rows = [
            {
                "id": record.chunk_id,
                "tenant_id": record.tenant_id,
                "document_id": record.document_id,
                "version_id": record.version_id,
                "index_version": record.index_version,
                "embedding": list(record.embedding),
            }
            for record in records
        ]
        self._client.upsert(collection_name=self._collection, data=rows)
        return len(rows)

    def search(
        self,
        *,
        tenant_id: str,
        index_version: str,
        embedding: Sequence[float],
        limit: int,
    ) -> list[dict]:
        if not tenant_id or not index_version:
            raise ValueError("tenant_id_and_index_version_are_required")
        expression = f'tenant_id == "{_escape(tenant_id)}" and index_version == "{_escape(index_version)}"'
        return self._client.search(
            collection_name=self._collection,
            data=[list(embedding)],
            filter=expression,
            limit=limit,
            output_fields=["tenant_id", "document_id", "version_id", "index_version"],
        )[0]


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
