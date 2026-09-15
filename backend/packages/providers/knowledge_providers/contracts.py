from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field


class ProviderMode(StrEnum):
    MOCK = "mock"
    LIVE = "live"


class MinerUArtifact(BaseModel):
    markdown: str
    page_count: int = Field(ge=1)
    tables: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)


class DocumentAnalysis(BaseModel):
    title: str
    document_type: str
    summary: str
    category_suggestion: str
    sensitivity_suggestion: str
    chunk_strategy: str
    warnings: list[str] = Field(default_factory=list)


class MinerUProvider(Protocol):
    mode: ProviderMode

    def parse(self, *, filename: str, content: bytes) -> MinerUArtifact: ...


class DocumentAnalyzer(Protocol):
    mode: ProviderMode

    def analyze(self, artifact: MinerUArtifact) -> DocumentAnalysis: ...


class EmbeddingProvider(Protocol):
    mode: ProviderMode
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...

