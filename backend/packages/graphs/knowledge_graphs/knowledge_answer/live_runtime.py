from __future__ import annotations

from hashlib import sha256
import json

from agent_harness import AgentRunner
from knowledge_providers.mcp import StreamableHttpMcpClient
from knowledge_providers.siliconflow import (
    SiliconFlowClient, SiliconFlowEmbeddingProvider, SiliconFlowGeneralKnowledgeSource,
    SiliconFlowModelInvoker, SiliconFlowReranker,
)
from knowledge_retrieval import AuthorizedMilvusRetriever
from knowledge_vector_store.milvus import MilvusVectorStore

from .mock_runtime import EmptyMcpResearcher
from .runtime import AnswerRuntime, Evidence


class DashScopeMcpResearcher:
    def __init__(self, client: StreamableHttpMcpClient, *, tool_name: str = "") -> None:
        self.client, self.tool_name = client, tool_name

    def research(self, *, query: str) -> list[Evidence]:
        result = self.client.call_search(query, tool_name=self.tool_name)
        parts: list[str] = []
        for item in result.get("content", []):
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        if structured := result.get("structuredContent"):
            parts.append(json.dumps(structured, ensure_ascii=False))
        text = "\n".join(part for part in parts if part).strip()
        if not text:
            return []
        evidence_id = "mcp-" + sha256(text.encode()).hexdigest()[:24]
        return [Evidence(evidence_id=evidence_id, source_type="mcp", title="百炼联网搜索",
                         excerpt=text[:6000], score=0.7)]


class GeneralSourceAdapter:
    def __init__(self, source: SiliconFlowGeneralKnowledgeSource) -> None:
        self.source = source

    def generate_evidence(self, *, query: str) -> list[Evidence]:
        text = self.source.generate(query)
        evidence_id = "general-" + sha256(text.encode()).hexdigest()[:24]
        return [Evidence(evidence_id=evidence_id, source_type="general", title="模型一般知识",
                         excerpt=text[:6000], score=0.35)]


def build_live_answer_runtime(settings, database) -> AnswerRuntime:
    client = SiliconFlowClient(base_url=settings.siliconflow_base_url, api_key=settings.siliconflow_api_key)
    embedder = SiliconFlowEmbeddingProvider(client, model=settings.embedding_model)
    reranker = SiliconFlowReranker(client, model=settings.rerank_model)
    vector_store = MilvusVectorStore(
        uri=settings.milvus_uri, token=settings.milvus_token or None, collection=settings.milvus_collection
    )
    local = AuthorizedMilvusRetriever(
        database=database, vector_store=vector_store, embedder=embedder, reranker=reranker,
        index_version=settings.index_version,
    )
    if settings.mcp_mode == "live":
        mcp = DashScopeMcpResearcher(
            StreamableHttpMcpClient(url=settings.mcp_url, api_key=settings.mcp_api_key),
            tool_name=settings.mcp_tool_name,
        )
    else:
        mcp = EmptyMcpResearcher()
    return AnswerRuntime(
        runner=AgentRunner(SiliconFlowModelInvoker(client, model=settings.chat_model), provider_mode="live"),
        local_retriever=local, mcp_researcher=mcp,
        general_source=GeneralSourceAdapter(SiliconFlowGeneralKnowledgeSource(client, model=settings.chat_model)),
    )
