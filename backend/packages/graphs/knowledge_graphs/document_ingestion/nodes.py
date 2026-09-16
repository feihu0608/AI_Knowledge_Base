from __future__ import annotations

from hashlib import sha256
from typing import Any

from knowledge_vector_store.contracts import VectorRecord

from .runtime import IngestionRuntime
from .state import IngestionState


def _chunk(markdown: str, *, max_chars: int = 500) -> list[dict[str, Any]]:
    paragraphs = [part.strip() for part in markdown.split("\n\n") if part.strip()]
    chunks: list[dict[str, Any]] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}".strip()
        if buffer and len(candidate) > max_chars:
            chunks.append({"ordinal": len(chunks), "text": buffer})
            buffer = paragraph
        else:
            buffer = candidate
    if buffer:
        chunks.append({"ordinal": len(chunks), "text": buffer})
    return chunks


def build_nodes(runtime: IngestionRuntime):
    def report(stage: str, completed: int) -> None:
        if runtime.progress_callback:
            runtime.progress_callback(stage, completed, 7)

    def validate_file(state: IngestionState) -> dict:
        if not state["content"]:
            return {"stage": "failed", "status": "failed", "error_code": "empty_document"}
        extension = state["filename"].rsplit(".", 1)[-1].lower()
        if extension not in {"pdf", "md", "txt", "doc", "docx"}:
            return {"stage": "failed", "status": "failed", "error_code": "unsupported_format"}
        report("parsing", 1)
        return {"stage": "validated"}

    def parse_document(state: IngestionState) -> dict:
        artifact = runtime.mineru.parse(filename=state["filename"], content=state["content"])
        report("analyzing", 2)
        return {
            "stage": "parsed",
            "parsed_markdown": artifact.markdown,
            "warnings": artifact.warnings,
        }

    def analyze_document(state: IngestionState) -> dict:
        from knowledge_providers.contracts import MinerUArtifact

        artifact = MinerUArtifact(markdown=state["parsed_markdown"], page_count=1)
        analysis = runtime.analyzer.analyze(artifact)
        report("chunking", 3)
        return {"stage": "analyzed", "analysis": analysis.model_dump()}

    def build_chunks(state: IngestionState) -> dict:
        chunks = _chunk(state["parsed_markdown"])
        report("embedding", 4)
        return {"stage": "chunked", "chunks": chunks}

    def embed_chunks(state: IngestionState) -> dict:
        vectors = runtime.embedder.embed([chunk["text"] for chunk in state["chunks"]])
        report("indexing", 5)
        return {"stage": "embedded", "embeddings": vectors}

    def index_chunks(state: IngestionState) -> dict:
        records = []
        for chunk, vector in zip(state["chunks"], state["embeddings"], strict=True):
            chunk_id = sha256(
                f'{state["tenant_id"]}:{state["version_id"]}:{chunk["ordinal"]}'.encode("utf-8")
            ).hexdigest()[:32]
            records.append(
                VectorRecord(
                    chunk_id=chunk_id,
                    tenant_id=state["tenant_id"],
                    document_id=state["document_id"],
                    version_id=state["version_id"],
                    index_version=state["index_version"],
                    embedding=tuple(vector),
                )
            )
        count = runtime.vector_store.upsert(records)
        report("publishing", 6)
        return {"stage": "indexed", "indexed_count": count}

    def publish_version(state: IngestionState) -> dict:
        if state.get("indexed_count") != len(state.get("chunks", [])):
            return {"stage": "failed", "status": "failed", "error_code": "index_count_mismatch"}
        report("published", 7)
        return {"stage": "published", "status": "succeeded"}

    return validate_file, parse_document, analyze_document, build_chunks, embed_chunks, index_chunks, publish_version
