from __future__ import annotations

import hashlib
import re

from .contracts import DocumentAnalysis, MinerUArtifact, ProviderMode


class MockMinerUProvider:
    mode = ProviderMode.MOCK

    def parse(self, *, filename: str, content: bytes) -> MinerUArtifact:
        text = content.decode("utf-8", errors="replace").strip()
        if not text:
            raise ValueError("empty_document")
        return MinerUArtifact(markdown=text, page_count=1, warnings=["mock_parser_used"])


class MockDocumentAnalyzer:
    mode = ProviderMode.MOCK

    def analyze(self, artifact: MinerUArtifact) -> DocumentAnalysis:
        first_line = next((line.strip("# ") for line in artifact.markdown.splitlines() if line.strip()), "未命名文档")
        return DocumentAnalysis(
            title=first_line[:120],
            document_type="policy" if "制度" in artifact.markdown else "general",
            summary=artifact.markdown[:240],
            category_suggestion="制度" if "制度" in artifact.markdown else "通用",
            sensitivity_suggestion="internal",
            chunk_strategy="heading_aware" if re.search(r"(?m)^#{1,6} ", artifact.markdown) else "token_window",
            warnings=["mock_llm_analysis_used"],
        )


class MockEmbeddingProvider:
    mode = ProviderMode.MOCK
    model = "mock/sha256-embedding"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vectors.append([round(byte / 255.0, 6) for byte in digest[:8]])
        return vectors

