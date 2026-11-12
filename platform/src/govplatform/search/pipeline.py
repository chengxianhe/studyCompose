"""Index-ready hybrid retrieval, local reranking, and evidence grading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from govplatform.ingest.es_index import elasticsearch_client, require_ready_index
from govplatform.knowledge.models import KnowledgeObject
from govplatform.search.es_retriever import ChunkHit, retrieve
from govplatform.search.rerank import RankedHit, has_relevant_evidence, rerank_hits

Grade = Literal["pass", "retry", "insufficient", "unavailable"]


@dataclass(frozen=True)
class PipelineResult:
    hits: list[RankedHit]
    grade: Grade
    used_vector: bool
    reranker_used: bool


def enabled() -> bool:
    return bool(os.environ.get("GOVPLAT_ES_URL"))


def search_chunks(
    *,
    query: str,
    index_objects: list[KnowledgeObject],
    authorized_objects: list[KnowledgeObject],
    limit: int,
    attempt: int,
) -> PipelineResult:
    if not 0 <= attempt <= 2:
        raise ValueError("attempt must be between 0 and 2")
    client = elasticsearch_client()
    try:
        require_ready_index(client, index_objects)
        retrieved = retrieve(client, query)
    finally:
        client.close()
    current = {obj.knowledge_id: obj for obj in authorized_objects}
    authorized: list[ChunkHit] = []
    for hit in retrieved.hits:
        obj = current.get(hit.parent_id)
        if obj is None or obj.version != hit.parent_version or obj.content_hash != hit.content_hash:
            continue
        authorized.append(hit)
    try:
        ranked = rerank_hits(query, authorized, limit=limit)
    except (OSError, ValueError, RuntimeError):
        return PipelineResult(
            hits=[RankedHit(hit, 0.0) for hit in authorized[:limit]],
            grade="unavailable",
            used_vector=retrieved.used_vector,
            reranker_used=False,
        )
    if has_relevant_evidence(ranked):
        return PipelineResult(ranked, "pass", retrieved.used_vector, True)
    grade: Grade = "retry" if attempt < 2 else "insufficient"
    return PipelineResult([], grade, retrieved.used_vector, True)
