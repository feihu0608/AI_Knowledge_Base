from agent_harness import AgentRunner
from knowledge_graphs.knowledge_answer import AnswerRuntime, Evidence, build_knowledge_answer_graph


class FakeLocalRetriever:
    def search(self, *, tenant_id: str, user_id: str, query: str) -> list[Evidence]:
        return [
            Evidence(evidence_id="local-allowed", source_type="local", title="差旅制度", excerpt="报销期限30天",
                     score=0.95, tenant_id=tenant_id, source_id="doc-1", source_version="v1",
                     acl_version=2, acl_allowed=True),
            Evidence(evidence_id="local-denied", source_type="local", title="薪酬", excerpt="受限正文",
                     score=1.0, tenant_id=tenant_id, source_id="doc-secret", acl_allowed=False),
            Evidence(evidence_id="cross-tenant", source_type="local", title="其他租户", excerpt="不可见",
                     score=1.0, tenant_id="tenant-b", source_id="doc-b", acl_allowed=True),
        ]


class FakeMcpResearcher:
    def research(self, *, query: str) -> list[Evidence]:
        return [Evidence(evidence_id="mcp-1", source_type="mcp", title="外部规范", excerpt="应保留票据", score=0.8)]


class FakeGeneralSource:
    def generate_evidence(self, *, query: str) -> list[Evidence]:
        return [Evidence(evidence_id="general-1", source_type="general", title="一般知识", excerpt="以公司制度为准", score=0.4)]


def fake_model(definition, input_data: dict) -> dict:
    if definition.name == "QueryPlannerAgent":
        return {"use_local": True, "use_mcp": True, "use_general": True,
                "rewritten_query": input_data["question"].strip()}
    return {"answer": "差旅报销应在30天内完成，并保留票据。[local-allowed][mcp-1]",
            "citation_ids": ["local-allowed", "mcp-1", "fabricated-id"]}


def test_three_way_answer_graph_filters_acl_and_invalid_citations() -> None:
    runtime = AnswerRuntime(
        runner=AgentRunner(fake_model, provider_mode="mock"),
        local_retriever=FakeLocalRetriever(), mcp_researcher=FakeMcpResearcher(),
        general_source=FakeGeneralSource(),
    )
    result = build_knowledge_answer_graph(runtime).invoke({
        "tenant_id": "tenant-a", "user_id": "alice", "question": "差旅怎么报销？",
        "provider_mode": "mock", "status": "requested",
    })
    evidence_ids = [item["evidence_id"] for item in result["fused_evidence"]]
    assert evidence_ids == ["local-allowed", "mcp-1", "general-1"]
    assert result["citation_ids"] == ["local-allowed", "mcp-1"]
    assert result["warnings"] == ["invalid_citations_removed"]
    assert result["status"] == "succeeded"
