from __future__ import annotations

from .agents import ANSWER_WRITER, QUERY_PLANNER
from .runtime import AnswerRuntime, Evidence
from .state import AnswerState


def build_nodes(runtime: AnswerRuntime):
    def plan_query(state: AnswerState) -> dict:
        result = runtime.runner.run(QUERY_PLANNER, {"question": state["question"]})
        return {"plan": result.output.model_dump(), "status": "planned"}

    def retrieve_local(state: AnswerState) -> dict:
        if not state["plan"]["use_local"]:
            return {"local_evidence": []}
        evidence = runtime.local_retriever.search(
            tenant_id=state["tenant_id"], user_id=state["user_id"], query=state["plan"]["rewritten_query"]
        )
        # A provider cannot grant access. Local evidence must carry a positive deterministic ACL decision.
        allowed = [item for item in evidence if item.tenant_id == state["tenant_id"] and item.acl_allowed]
        return {"local_evidence": [item.model_dump() for item in allowed]}

    def research_mcp(state: AnswerState) -> dict:
        if not state["plan"]["use_mcp"]:
            return {"mcp_evidence": []}
        evidence = runtime.mcp_researcher.research(query=state["plan"]["rewritten_query"])
        return {"mcp_evidence": [item.model_dump() for item in evidence]}

    def generate_general(state: AnswerState) -> dict:
        if not state["plan"]["use_general"]:
            return {"general_evidence": []}
        evidence = runtime.general_source.generate_evidence(query=state["plan"]["rewritten_query"])
        return {"general_evidence": [item.model_dump() for item in evidence]}

    def fuse_evidence(state: AnswerState) -> dict:
        candidates = [
            *state.get("local_evidence", []), *state.get("mcp_evidence", []), *state.get("general_evidence", [])
        ]
        best: dict[str, Evidence] = {}
        for raw in candidates:
            item = Evidence.model_validate(raw)
            previous = best.get(item.evidence_id)
            if previous is None or item.score > previous.score:
                best[item.evidence_id] = item
        priority = {"local": 0, "mcp": 1, "general": 2}
        ordered = sorted(best.values(), key=lambda item: (priority.get(item.source_type, 9), -item.score))
        fused = ordered[:runtime.max_fused_evidence]
        return {"fused_evidence": [item.model_dump() for item in fused], "status": "evidence_fused"}

    def write_answer(state: AnswerState) -> dict:
        result = runtime.runner.run(ANSWER_WRITER, {
            "question": state["question"], "evidence": state.get("fused_evidence", [])
        })
        return {"answer": result.output.answer, "citation_ids": result.output.citation_ids, "status": "drafted"}

    def validate_answer(state: AnswerState) -> dict:
        valid_ids = {item["evidence_id"] for item in state.get("fused_evidence", [])}
        citations = list(dict.fromkeys(item for item in state.get("citation_ids", []) if item in valid_ids))
        warnings = []
        if len(citations) != len(state.get("citation_ids", [])):
            warnings.append("invalid_citations_removed")
        if not valid_ids:
            warnings.append("no_evidence")
        return {"citation_ids": citations, "warnings": warnings, "status": "succeeded"}

    return plan_query, retrieve_local, research_mcp, generate_general, fuse_evidence, write_answer, validate_answer
