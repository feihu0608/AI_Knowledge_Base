from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class VectorRecord:
    chunk_id: str
    tenant_id: str
    document_id: str
    version_id: str
    index_version: str
    embedding: tuple[float, ...]


class VectorStore(Protocol):
    def upsert(self, records: Sequence[VectorRecord]) -> int: ...
    def count(self, *, tenant_id: str, index_version: str) -> int: ...

