from langgraph.graph import END, START, StateGraph

from .nodes import build_nodes
from .runtime import AnswerRuntime
from .state import AnswerState


def build_knowledge_answer_graph(runtime: AnswerRuntime):
    plan, local, mcp, general, fuse, write, validate = build_nodes(runtime)
    graph = StateGraph(AnswerState)
    graph.add_node("plan_query", plan)
    graph.add_node("retrieve_local", local)
    graph.add_node("research_mcp", mcp)
    graph.add_node("generate_general", general)
    graph.add_node("fuse_evidence", fuse)
    graph.add_node("write_answer", write)
    graph.add_node("validate_answer", validate)
    graph.add_edge(START, "plan_query")
    graph.add_edge("plan_query", "retrieve_local")
    graph.add_edge("plan_query", "research_mcp")
    graph.add_edge("plan_query", "generate_general")
    graph.add_edge(["retrieve_local", "research_mcp", "generate_general"], "fuse_evidence")
    graph.add_edge("fuse_evidence", "write_answer")
    graph.add_edge("write_answer", "validate_answer")
    graph.add_edge("validate_answer", END)
    return graph.compile()
