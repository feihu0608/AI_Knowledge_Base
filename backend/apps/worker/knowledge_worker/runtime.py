from __future__ import annotations

import os

from knowledge_application.storage import LocalObjectStorage
from knowledge_graphs.document_ingestion import build_document_ingestion_graph
from knowledge_graphs.document_ingestion.runtime import IngestionRuntime
from knowledge_persistence import Database
from knowledge_providers.mock import MockDocumentAnalyzer, MockEmbeddingProvider, MockMinerUProvider
from knowledge_providers.document_parser import RoutingDocumentParser
from knowledge_providers.mineru import MinerUApiProvider
from knowledge_providers.siliconflow import (
    SiliconFlowClient, SiliconFlowDocumentAnalyzer, SiliconFlowEmbeddingProvider,
)
from knowledge_vector_store.memory import InMemoryVectorStore
from knowledge_vector_store.milvus import MilvusVectorStore


database = Database(os.getenv("DATABASE_URL", "sqlite:///./storage/knowledge.db"))
storage = LocalObjectStorage(os.getenv("STORAGE_DIR", "storage/objects"))


def build_ingestion_graph():
    parser_mode = os.getenv("PARSER_MODE", "mock")
    ai_mode = os.getenv("AI_MODE", "mock")
    if parser_mode == "live":
        mineru = RoutingDocumentParser(
            mineru=MinerUApiProvider(
                base_url=os.getenv("MINERU_BASE_URL", "https://mineru.net/api/v4"),
                api_key=os.environ["MINERU_API_KEY"],
            ),
        )
    else:
        mineru = MockMinerUProvider()
    if ai_mode == "live":
        client = SiliconFlowClient(
            base_url=os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
            api_key=os.environ["SILICONFLOW_API_KEY"],
        )
        analyzer = SiliconFlowDocumentAnalyzer(client, model=os.getenv("CHAT_MODEL", "deepseek-ai/DeepSeek-V3"))
        embedder = SiliconFlowEmbeddingProvider(client, model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5"))
        vector_store = MilvusVectorStore(
            uri=os.getenv("MILVUS_URI", "http://milvus:19530"), token=os.getenv("MILVUS_TOKEN") or None,
            collection=os.getenv("MILVUS_COLLECTION", "knowledge_chunks_v1"),
        )
        vector_store.ensure_collection(dimension=int(os.getenv("EMBEDDING_DIMENSION", "1024")))
    else:
        analyzer, embedder, vector_store = MockDocumentAnalyzer(), MockEmbeddingProvider(), InMemoryVectorStore()
    return build_document_ingestion_graph(IngestionRuntime(
        mineru=mineru, analyzer=analyzer, embedder=embedder, vector_store=vector_store,
    ))
