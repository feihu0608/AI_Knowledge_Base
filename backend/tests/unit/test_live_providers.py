import json

import httpx

from knowledge_providers.mcp import StreamableHttpMcpClient
from knowledge_providers.siliconflow import SiliconFlowClient, SiliconFlowEmbeddingProvider, SiliconFlowReranker


def test_siliconflow_embedding_and_rerank_contracts() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(200, json={"data": [
                {"index": 1, "embedding": [0.3, 0.4]}, {"index": 0, "embedding": [0.1, 0.2]},
            ]})
        assert body["top_n"] == 1
        return httpx.Response(200, json={"results": [{"index": 1, "relevance_score": 0.91}]})

    client = SiliconFlowClient(
        base_url="https://provider.invalid/v1", api_key="test-token",
        transport=httpx.MockTransport(handler),
    )
    vectors = SiliconFlowEmbeddingProvider(client, model="embedding-model").embed(["甲", "乙"])
    reranked = SiliconFlowReranker(client, model="rerank-model").rerank("问题", ["甲", "乙"], top_n=1)
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert reranked == [(1, 0.91)]
    assert all(request.headers["authorization"] == "Bearer test-token" for request in requests)


def test_streamable_http_mcp_initializes_lists_and_calls_search() -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        methods.append(body["method"])
        if body["method"] == "initialize":
            payload = {"jsonrpc": "2.0", "id": body["id"], "result": {"protocolVersion": "2025-03-26"}}
            return httpx.Response(200, json=payload, headers={"Mcp-Session-Id": "session-a"})
        if body["method"] == "notifications/initialized":
            assert request.headers["mcp-session-id"] == "session-a"
            return httpx.Response(202)
        if body["method"] == "tools/list":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": {"tools": [
                {"name": "web_search", "inputSchema": {"properties": {"query": {"type": "string"}}}}
            ]}})
        assert body["params"]["arguments"] == {"query": "Milvus"}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"],
                                         "result": {"content": [{"type": "text", "text": "result"}]}})

    client = StreamableHttpMcpClient(
        url="https://mcp.invalid", api_key="test-token", transport=httpx.MockTransport(handler)
    )
    result = client.call_search("Milvus")
    assert result["content"][0]["text"] == "result"
    assert methods == ["initialize", "notifications/initialized", "tools/list", "tools/call"]
