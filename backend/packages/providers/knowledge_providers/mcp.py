from __future__ import annotations

import json
from typing import Any
import httpx


class McpProtocolError(RuntimeError):
    pass


class StreamableHttpMcpClient:
    def __init__(self, *, url: str, api_key: str, timeout_seconds: float = 60,
                 transport: httpx.BaseTransport | None = None) -> None:
        if not url or not api_key:
            raise ValueError("MCP_URL and MCP_API_KEY are required in live mode")
        self.url = url
        self._session_id: str | None = None
        self._request_id = 0
        self._client = httpx.Client(
            timeout=timeout_seconds, transport=transport,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json, text/event-stream",
                     "Content-Type": "application/json"},
        )

    def _decode(self, response: httpx.Response) -> dict[str, Any]:
        response.raise_for_status()
        if session_id := response.headers.get("Mcp-Session-Id"):
            self._session_id = session_id
        if "text/event-stream" in response.headers.get("content-type", ""):
            payloads = [line[5:].strip() for line in response.text.splitlines() if line.startswith("data:")]
            if not payloads:
                raise McpProtocolError("MCP returned an empty event stream")
            data = json.loads(payloads[-1])
        else:
            data = response.json()
        if not isinstance(data, dict) or "error" in data:
            raise McpProtocolError("MCP returned a protocol error")
        return data

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._request_id += 1
        headers = {"Mcp-Session-Id": self._session_id} if self._session_id else None
        response = self._client.post(self.url, headers=headers, json={
            "jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params or {},
        })
        return self._decode(response).get("result", {})

    def initialize(self) -> None:
        self.request("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                    "clientInfo": {"name": "ai-knowledge-base", "version": "0.1.0"}})
        headers = {"Mcp-Session-Id": self._session_id} if self._session_id else None
        response = self._client.post(self.url, headers=headers, json={
            "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
        })
        response.raise_for_status()

    def call_search(self, query: str, *, tool_name: str = "") -> dict[str, Any]:
        self.initialize()
        tools = self.request("tools/list").get("tools", [])
        selected = next((item for item in tools if item.get("name") == tool_name), None) if tool_name else None
        selected = selected or next((item for item in tools if "search" in item.get("name", "").lower()), None)
        if selected is None:
            raise McpProtocolError("no web search tool advertised by MCP server")
        properties = selected.get("inputSchema", {}).get("properties", {})
        query_key = next((key for key in ("query", "q", "keywords", "search_query") if key in properties), "query")
        return self.request("tools/call", {"name": selected["name"], "arguments": {query_key: query}})
