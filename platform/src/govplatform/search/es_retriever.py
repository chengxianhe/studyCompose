"""Elasticsearch BM25 and dense-vector child recall with application-side RRF."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from elasticsearch import Elasticsearch

from govplatform import embedding
from govplatform.ingest.es_index import index_alias

_RECALL_WINDOW = 40
_RETRIEVED = 30
_RRF_CONSTANT = 60


@dataclass(frozen=True)
class ChunkHit:
    chunk_id: str
    parent_id: str
    parent_version: int
    heading_path: tuple[str, ...]
    text: str
    source: str
    content_hash: str
    retrieval_score: float


@dataclass(frozen=True)
class Retrieval:
    hits: list[ChunkHit]
    used_vector: bool


def retrieve(client: Elasticsearch, query: str) -> Retrieval:
    vector: list[float] | None
    try:
        vector = np.frombuffer(embedding.embed(query), dtype="float32").tolist()
        if len(vector) != 512:
            vector = None
    except Exception:
        vector = None

    lexical = client.search(
        index=index_alias(),
        query={"match": {"bm25_field": query}},
        size=_RECALL_WINDOW,
        source_excludes=["knn_vector"],
    )
    lexical_rows = lexical["hits"]["hits"]
    vector_rows: list[dict[str, Any]] = []
    if vector is not None:
        semantic = client.search(
            index=index_alias(),
            knn={
                "field": "knn_vector",
                "query_vector": vector,
                "k": _RECALL_WINDOW,
                "num_candidates": 100,
            },
            size=_RECALL_WINDOW,
            source_excludes=["knn_vector"],
        )
        vector_rows = list(semantic["hits"]["hits"])
    rows_by_id = {str(row["_id"]): row for row in [*lexical_rows, *vector_rows]}
    scores: dict[str, float] = {}
    for rows in (lexical_rows, vector_rows):
        for rank, row in enumerate(rows, start=1):
            chunk_id = str(row["_id"])
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (_RRF_CONSTANT + rank)
    ranked_ids = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
    hits: list[ChunkHit] = []
    for chunk_id in ranked_ids[:_RETRIEVED]:
        source = rows_by_id[chunk_id]["_source"]
        hits.append(
            ChunkHit(
                chunk_id=source["chunk_id"],
                parent_id=source["parent_id"],
                parent_version=source["parent_version"],
                heading_path=tuple(source["heading_path"]),
                text=source["text"],
                source=source["source"],
                content_hash=source["content_hash"],
                retrieval_score=scores[chunk_id],
            )
        )
    return Retrieval(hits=hits, used_vector=bool(vector_rows))
