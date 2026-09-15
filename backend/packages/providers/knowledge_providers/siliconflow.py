from __future__ import annotations

import json
from typing import Any
import httpx

from .contracts import DocumentAnalysis, MinerUArtifact, ProviderMode


class ProviderConfigurationError(RuntimeError):
    pass


class SiliconFlowClient:
    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: float = 60,
                 transport: httpx.BaseTransport | None = None) -> None:
        if not api_key:
            raise ProviderConfigurationError("SILICONFLOW_API_KEY is required in live mode")
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds, transport=transport,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(path, json=payload)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("provider returned a non-object response")
        return data

    def chat_text(self, *, model: str, system: str, user: str) -> str:
        data = self.post("/chat/completions", {
            "model": model, "messages": [{"role": "system", "content": system},
                                           {"role": "user", "content": user}], "temperature": 0.1,
        })
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("provider response is missing assistant content") from exc

    def chat_json(self, *, model: str, system: str, user: str) -> dict[str, Any]:
        data = self.post("/chat/completions", {
            "model": model, "messages": [{"role": "system", "content": system},
                                           {"role": "user", "content": user}],
            "temperature": 0.0, "response_format": {"type": "json_object"},
        })
        try:
            content = str(data["choices"][0]["message"]["content"]).strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise TypeError
            return parsed
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("provider did not return valid JSON") from exc


class SiliconFlowEmbeddingProvider:
    mode = ProviderMode.LIVE

    def __init__(self, client: SiliconFlowClient, *, model: str) -> None:
        self.client, self.model = client, model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        data = self.client.post("/embeddings", {"model": self.model, "input": texts})
        rows = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
        vectors = [[float(value) for value in row["embedding"]] for row in rows]
        if len(vectors) != len(texts):
            raise RuntimeError("embedding count mismatch")
        return vectors


class SiliconFlowReranker:
    def __init__(self, client: SiliconFlowClient, *, model: str) -> None:
        self.client, self.model = client, model

    def rerank(self, query: str, documents: list[str], *, top_n: int) -> list[tuple[int, float]]:
        if not documents:
            return []
        data = self.client.post("/rerank", {"model": self.model, "query": query, "documents": documents,
                                            "top_n": min(top_n, len(documents)), "return_documents": False})
        return [(int(row["index"]), float(row["relevance_score"])) for row in data.get("results", [])]


class SiliconFlowDocumentAnalyzer:
    mode = ProviderMode.LIVE

    def __init__(self, client: SiliconFlowClient, *, model: str) -> None:
        self.client, self.model = client, model

    def analyze(self, artifact: MinerUArtifact) -> DocumentAnalysis:
        raw = self.client.chat_json(
            model=self.model, system="你是企业文档分析器。仅输出符合 schema 的 JSON；不得决定最终权限。",
            user=json.dumps({"schema": DocumentAnalysis.model_json_schema(),
                             "document": artifact.markdown[:16000]}, ensure_ascii=False),
        )
        return DocumentAnalysis.model_validate(raw)


class SiliconFlowModelInvoker:
    def __init__(self, client: SiliconFlowClient, *, model: str) -> None:
        self.client, self.model = client, model

    def __call__(self, definition, input_data: dict[str, Any]) -> dict[str, Any]:
        return self.client.chat_json(
            model=self.model,
            system=("你是企业知识问答系统中的受控 Agent。只能返回符合 schema 的 JSON。"
                    "引用只能使用 evidence 中存在的 evidence_id；不得声称拥有或改变权限。"),
            user=json.dumps({"agent": definition.name, "schema": definition.output_schema.model_json_schema(),
                             "input": input_data}, ensure_ascii=False),
        )


class SiliconFlowGeneralKnowledgeSource:
    def __init__(self, client: SiliconFlowClient, *, model: str) -> None:
        self.client, self.model = client, model

    def generate(self, query: str) -> str:
        return self.client.chat_text(
            model=self.model,
            system="给出简洁的一般知识背景，并说明企业内部规则应以授权的内部文档为准。",
            user=query,
        )
