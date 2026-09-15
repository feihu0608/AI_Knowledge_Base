from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_harness import AgentRunner
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    evidence_id: str
    source_type: str
    title: str
    excerpt: str
    score: float = Field(ge=0, le=1)
    tenant_id: str | None = None
    source_id: str | None = None
    source_version: str | None = None
    acl_version: int | None = None
    acl_allowed: bool = False


class LocalRetriever(Protocol):
    def search(self, *, tenant_id: str, user_id: str, query: str) -> list[Evidence]: ...


class McpResearcher(Protocol):
    def research(self, *, query: str) -> list[Evidence]: ...


class GeneralKnowledgeSource(Protocol):
    def generate_evidence(self, *, query: str) -> list[Evidence]: ...


@dataclass(slots=True)
class AnswerRuntime:
    runner: AgentRunner
    local_retriever: LocalRetriever
    mcp_researcher: McpResearcher
    general_source: GeneralKnowledgeSource
    max_fused_evidence: int = 12
