from __future__ import annotations

from typing import NotRequired, TypedDict


class IngestionState(TypedDict):
    tenant_id: str
    actor_id: str
    knowledge_base_id: str
    document_id: str
    version_id: str
    filename: str
    content: bytes
    provider_mode: str
    stage: str
    index_version: str
    parsed_markdown: NotRequired[str]
    analysis: NotRequired[dict]
    chunks: NotRequired[list[dict]]
    embeddings: NotRequired[list[list[float]]]
    indexed_count: NotRequired[int]
    warnings: NotRequired[list[str]]
    status: NotRequired[str]
    error_code: NotRequired[str]

