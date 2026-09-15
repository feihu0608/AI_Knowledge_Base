from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes import build_nodes
from .routes import route_after_validation
from .runtime import IngestionRuntime
from .state import IngestionState


def build_document_ingestion_graph(runtime: IngestionRuntime):
    validate, parse, analyze, chunk, embed, index, publish = build_nodes(runtime)
    graph = StateGraph(IngestionState)
    graph.add_node("validate_file", validate)
    graph.add_node("parse_document", parse)
    graph.add_node("analyze_document", analyze)
    graph.add_node("build_chunks", chunk)
    graph.add_node("embed_chunks", embed)
    graph.add_node("index_chunks", index)
    graph.add_node("publish_version", publish)
    graph.add_edge(START, "validate_file")
    graph.add_conditional_edges(
        "validate_file",
        route_after_validation,
        {"parse_document": "parse_document", "failed": END},
    )
    graph.add_edge("parse_document", "analyze_document")
    graph.add_edge("analyze_document", "build_chunks")
    graph.add_edge("build_chunks", "embed_chunks")
    graph.add_edge("embed_chunks", "index_chunks")
    graph.add_edge("index_chunks", "publish_version")
    graph.add_edge("publish_version", END)
    return graph.compile()

