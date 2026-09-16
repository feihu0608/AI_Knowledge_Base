from knowledge_graphs.document_ingestion import IngestionRuntime, build_document_ingestion_graph
from knowledge_providers.mock import MockDocumentAnalyzer, MockEmbeddingProvider, MockMinerUProvider
from knowledge_vector_store import InMemoryVectorStore


def test_mock_ingestion_is_explicit_and_indexes_all_chunks():
    store = InMemoryVectorStore()
    progress = []
    runtime = IngestionRuntime(
        mineru=MockMinerUProvider(),
        analyzer=MockDocumentAnalyzer(),
        embedder=MockEmbeddingProvider(),
        vector_store=store,
        progress_callback=lambda stage, completed, total: progress.append((stage, completed, total)),
    )
    graph = build_document_ingestion_graph(runtime)
    result = graph.invoke(
        {
            "tenant_id": "tenant-a",
            "actor_id": "admin-a",
            "knowledge_base_id": "kb-a",
            "document_id": "doc-a",
            "version_id": "v1",
            "filename": "差旅制度.md",
            "content": "# 差旅制度\n\n住宿标准以审批后的城市等级为准。".encode(),
            "provider_mode": "mock",
            "stage": "queued",
            "index_version": "idx-v1",
        }
    )
    assert result["status"] == "succeeded"
    assert result["provider_mode"] == "mock"
    assert result["indexed_count"] == len(result["chunks"])
    assert store.count(tenant_id="tenant-a", index_version="idx-v1") == result["indexed_count"]
    assert progress == [
        ("parsing", 1, 7), ("analyzing", 2, 7), ("chunking", 3, 7),
        ("embedding", 4, 7), ("indexing", 5, 7), ("publishing", 6, 7),
        ("published", 7, 7),
    ]


def test_unsupported_file_stops_before_provider_calls():
    runtime = IngestionRuntime(
        mineru=MockMinerUProvider(),
        analyzer=MockDocumentAnalyzer(),
        embedder=MockEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
    )
    result = build_document_ingestion_graph(runtime).invoke(
        {
            "tenant_id": "tenant-a",
            "actor_id": "admin-a",
            "knowledge_base_id": "kb-a",
            "document_id": "doc-a",
            "version_id": "v1",
            "filename": "unsafe.exe",
            "content": b"not allowed",
            "provider_mode": "mock",
            "stage": "queued",
            "index_version": "idx-v1",
        }
    )
    assert result["status"] == "failed"
    assert result["error_code"] == "unsupported_format"
