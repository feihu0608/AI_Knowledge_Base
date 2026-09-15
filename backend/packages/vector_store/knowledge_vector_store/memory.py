from __future__ import annotations

from collections.abc import Sequence

from .contracts import VectorRecord


class InMemoryVectorStore:
    """Deterministic test adapter. Responses must remain labelled mock."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], VectorRecord] = {}

    def upsert(self, records: Sequence[VectorRecord]) -> int:
        for record in records:
            key = (record.tenant_id, record.index_version, record.chunk_id)
            self._records[key] = record
        return len(records)

    def count(self, *, tenant_id: str, index_version: str) -> int:
        return sum(1 for tenant, version, _ in self._records if tenant == tenant_id and version == index_version)

