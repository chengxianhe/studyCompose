from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from govplatform.knowledge.models import KnowledgeObject

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_一-鿿]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Corpus:
    def __init__(self, objects: list[KnowledgeObject]) -> None:
        self._objects = objects
        corpus = [tokenize(f"{obj.title} {obj.title} {obj.body}") for obj in objects]
        self._doc_tokens = [set(tokens) for tokens in corpus]
        self._bm25: BM25Okapi | None = BM25Okapi(corpus) if corpus else None

    def query(self, text: str, limit: int) -> list[tuple[KnowledgeObject, float]]:
        if self._bm25 is None:
            return []
        query_tokens = tokenize(text)
        query_token_set = set(query_tokens)
        scores = self._bm25.get_scores(query_tokens)
        # BM25's score sign is unreliable with a tiny corpus (IDF math breaks
        # down with few documents, see docs/LESSONS.md-style note in README).
        # Literal token overlap gates relevance; BM25 score only orders hits.
        candidates = [
            (obj, float(score))
            for obj, score, doc_tokens in zip(self._objects, scores, self._doc_tokens, strict=True)
            if doc_tokens & query_token_set
        ]
        candidates.sort(key=lambda pair: pair[1], reverse=True)
        return candidates[:limit]
