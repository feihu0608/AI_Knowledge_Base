from __future__ import annotations

import os

from knowledge_application.storage import LocalObjectStorage
from knowledge_graphs.document_ingestion import build_document_ingestion_graph
from knowledge_graphs.document_ingestion.runtime import IngestionRuntime
from knowledge_persistence import Database
from knowledge_providers.mock import MockDocumentAnalyzer, MockEmbeddingProvider, MockMinerUProvider
from knowledge_vector_store.memory import InMemoryVectorStore


database = Database(os.getenv("DATABASE_URL", "sqlite:///./storage/knowledge.db"))
storage = LocalObjectStorage(os.getenv("STORAGE_DIR", "storage/objects"))


def build_ingestion_graph():
    mode = os.getenv("PROVIDER_MODE", "mock")
    if mode != "mock":
        raise RuntimeError("live ingestion providers are not configured yet")
    return build_document_ingestion_graph(IngestionRuntime(
        mineru=MockMinerUProvider(), analyzer=MockDocumentAnalyzer(),
        embedder=MockEmbeddingProvider(), vector_store=InMemoryVectorStore(),
    ))
