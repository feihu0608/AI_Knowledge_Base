from __future__ import annotations

from agent_harness import AgentRunner

from .runtime import AnswerRuntime, Evidence


class EmptyLocalRetriever:
    def search(self, *, tenant_id: str, user_id: str, query: str) -> list[Evidence]:
        return []


class EmptyMcpResearcher:
    def research(self, *, query: str) -> list[Evidence]:
        return []


class LabelledMockGeneralSource:
    def generate_evidence(self, *, query: str) -> list[Evidence]:
        return [Evidence(
            evidence_id="mock-general", source_type="general", title="Mock 一般知识",
            excerpt="当前未接通真实模型、MCP 或本地索引，此内容仅用于验证工作流。", score=0.1,
        )]


def _invoke(definition, input_data: dict) -> dict:
    if definition.name == "QueryPlannerAgent":
        return {"use_local": True, "use_mcp": True, "use_general": True,
                "rewritten_query": input_data["question"]}
    return {
        "answer": "[MOCK] 问答工作流已运行，但真实知识检索、魔搭 MCP 和硅基流动模型尚未接通。",
        "citation_ids": ["mock-general"],
    }


def build_mock_answer_runtime() -> AnswerRuntime:
    return AnswerRuntime(
        runner=AgentRunner(_invoke, provider_mode="mock"), local_retriever=EmptyLocalRetriever(),
        mcp_researcher=EmptyMcpResearcher(), general_source=LabelledMockGeneralSource(),
    )
