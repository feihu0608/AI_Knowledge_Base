from __future__ import annotations

from typing import NotRequired, TypedDict


class AnswerState(TypedDict):
    tenant_id: str
    user_id: str
    question: str
    provider_mode: str
    local_evidence: NotRequired[list[dict]]
    mcp_evidence: NotRequired[list[dict]]
    general_evidence: NotRequired[list[dict]]
    plan: NotRequired[dict]
    fused_evidence: NotRequired[list[dict]]
    answer: NotRequired[str]
    citation_ids: NotRequired[list[str]]
    status: NotRequired[str]
    warnings: NotRequired[list[str]]
