import json
from io import BytesIO
from zipfile import ZipFile

import httpx

from knowledge_providers.mcp import StreamableHttpMcpClient
from knowledge_providers.document_parser import PlainTextDocumentParser, RoutingDocumentParser
from knowledge_providers.mineru import MinerUApiProvider, MinerUParseError
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


def _markdown_zip(markdown: str = "# 标题\n\n正文") -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as bundle:
        bundle.writestr("result/full.md", markdown)
    return output.getvalue()


def test_mineru_upload_poll_and_markdown_contract() -> None:
    api_calls = 0
    file_requests: list[httpx.Request] = []

    def api_handler(request: httpx.Request) -> httpx.Response:
        nonlocal api_calls
        assert request.headers["authorization"] == "Bearer mineru-token"
        if request.url.path.endswith("/file-urls/batch"):
            api_calls += 1
            payload = json.loads(request.content)
            data_id = payload["files"][0]["data_id"]
            api_handler.data_id = data_id
            return httpx.Response(200, json={"code": 0, "data": {
                "batch_id": "batch-a", "file_urls": ["https://objects.invalid/upload"],
            }})
        api_calls += 1
        return httpx.Response(200, json={"code": 0, "data": {"extract_result": [{
            "data_id": api_handler.data_id, "state": "done",
            "full_zip_url": "https://objects.invalid/result.zip",
        }]}})

    def file_handler(request: httpx.Request) -> httpx.Response:
        file_requests.append(request)
        assert "authorization" not in request.headers
        if request.method == "PUT":
            assert request.content == b"document-bytes"
            assert "content-type" not in request.headers
            return httpx.Response(200)
        return httpx.Response(200, content=_markdown_zip("# 标题\n\n<!-- page 1 -->\n正文"))

    provider = MinerUApiProvider(
        base_url="https://mineru.invalid/api/v4", api_key="mineru-token",
        poll_interval_seconds=0, api_transport=httpx.MockTransport(api_handler),
        file_transport=httpx.MockTransport(file_handler),
    )
    artifact = provider.parse(filename="demo.pdf", content=b"document-bytes")
    assert artifact.markdown.startswith("# 标题")
    assert artifact.page_count == 1
    assert api_calls == 2
    assert [request.method for request in file_requests] == ["PUT", "GET"]


def test_mineru_surfaces_failed_parse() -> None:
    def api_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-urls/batch"):
            data_id = json.loads(request.content)["files"][0]["data_id"]
            api_handler.data_id = data_id
            return httpx.Response(200, json={"code": 0, "data": {
                "batch_id": "batch-a", "file_urls": ["https://objects.invalid/upload"],
            }})
        return httpx.Response(200, json={"code": 0, "data": {"extract_result": [{
            "data_id": api_handler.data_id, "state": "failed", "err_msg": "unsupported",
        }]}})

    provider = MinerUApiProvider(
        base_url="https://mineru.invalid/api/v4", api_key="mineru-token", poll_interval_seconds=0,
        api_transport=httpx.MockTransport(api_handler),
        file_transport=httpx.MockTransport(lambda request: httpx.Response(200)),
    )
    try:
        provider.parse(filename="bad.doc", content=b"bad")
    except MinerUParseError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("failed MinerU jobs must fail ingestion")


def test_mineru_rejects_archive_without_markdown() -> None:
    def api_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-urls/batch"):
            data_id = json.loads(request.content)["files"][0]["data_id"]
            api_handler.data_id = data_id
            return httpx.Response(200, json={"code": 0, "data": {
                "batch_id": "batch-a", "file_urls": ["https://objects.invalid/upload"],
            }})
        return httpx.Response(200, json={"code": 0, "data": {"extract_result": [{
            "data_id": api_handler.data_id, "state": "done",
            "full_zip_url": "https://objects.invalid/result.zip",
        }]}})

    output = BytesIO()
    with ZipFile(output, "w") as bundle:
        bundle.writestr("result.json", "{}")
    provider = MinerUApiProvider(
        base_url="https://mineru.invalid/api/v4", api_key="mineru-token", poll_interval_seconds=0,
        api_transport=httpx.MockTransport(api_handler),
        file_transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=output.getvalue())
        ),
    )
    try:
        provider.parse(filename="empty.pdf", content=b"document")
    except MinerUParseError as exc:
        assert "no Markdown" in str(exc)
    else:
        raise AssertionError("archives without Markdown must fail ingestion")


def test_mineru_times_out_when_job_never_finishes() -> None:
    def api_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-urls/batch"):
            return httpx.Response(200, json={"code": 0, "data": {
                "batch_id": "batch-a", "file_urls": ["https://objects.invalid/upload"],
            }})
        raise AssertionError("zero timeout must stop before polling")

    provider = MinerUApiProvider(
        base_url="https://mineru.invalid/api/v4", api_key="mineru-token", timeout_seconds=0,
        poll_interval_seconds=0, api_transport=httpx.MockTransport(api_handler),
        file_transport=httpx.MockTransport(lambda request: httpx.Response(200)),
    )
    try:
        provider.parse(filename="slow.pdf", content=b"document")
    except MinerUParseError as exc:
        assert "timed out" in str(exc)
    else:
        raise AssertionError("unfinished MinerU jobs must time out")


def test_routing_parser_handles_markdown_locally_and_rich_documents_with_mineru() -> None:
    class RecordingMinerU:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def parse(self, *, filename: str, content: bytes):
            self.calls.append(filename)
            return PlainTextDocumentParser().parse(filename="converted.md", content=b"# converted")

    mineru = RecordingMinerU()
    parser = RoutingDocumentParser(mineru=mineru)

    markdown = parser.parse(filename="policy.md", content="# 制度\n\n正文".encode())
    rich_document = parser.parse(filename="policy.docx", content=b"office-bytes")

    assert markdown.markdown.startswith("# 制度")
    assert markdown.warnings == ["native_text_parser_used"]
    assert rich_document.markdown == "# converted"
    assert mineru.calls == ["policy.docx"]


def test_plain_text_parser_accepts_gb18030() -> None:
    artifact = PlainTextDocumentParser().parse(filename="legacy.txt", content="旧版文本".encode("gb18030"))
    assert artifact.markdown == "旧版文本"
