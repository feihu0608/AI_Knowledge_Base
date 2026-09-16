from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from knowledge_providers.contracts import DocumentAnalyzer, EmbeddingProvider, MinerUProvider
from knowledge_vector_store.contracts import VectorStore


@dataclass(slots=True)
class IngestionRuntime:
    mineru: MinerUProvider
    analyzer: DocumentAnalyzer
    embedder: EmbeddingProvider
    vector_store: VectorStore
    progress_callback: Callable[[str, int, int], None] | None = None
