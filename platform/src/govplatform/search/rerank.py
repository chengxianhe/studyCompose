"""Local cross-encoder reranking and an explicit evidence decision."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from fastembed.rerank.cross_encoder import TextCrossEncoder

from govplatform.search.es_retriever import ChunkHit

_RERANK_INPUT_LIMIT = 20
_MIN_RELEVANCE = 0.5


@dataclass(frozen=True)
class RankedHit:
    hit: ChunkHit
    relevance_score: float


@lru_cache(maxsize=1)
def _model() -> TextCrossEncoder:
    from govplatform.rerank_model import load_model

    return load_model(allow_download=False)


def rerank_hits(query: str, hits: list[ChunkHit], limit: int) -> list[RankedHit]:
    selected = hits[:_RERANK_INPUT_LIMIT]
    if not selected:
        return []
    raw_scores = list(_model().rerank(query, [hit.text for hit in selected]))
    if len(raw_scores) != len(selected):
        raise ValueError("reranker returned a different number of scores")
    ranked = [
        RankedHit(hit, 1.0 / (1.0 + math.exp(-float(score))))
        for hit, score in zip(selected, raw_scores, strict=True)
    ]
    ranked.sort(key=lambda item: item.relevance_score, reverse=True)
    return ranked[:limit]


def has_relevant_evidence(hits: list[RankedHit]) -> bool:
    return bool(hits) and hits[0].relevance_score >= _MIN_RELEVANCE
