from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from govplatform.identity.models import Agent
from govplatform.knowledge.models import AuthorityLevel, KnowledgeObject, KnowledgeType
from govplatform.search import pipeline
from govplatform.search.es_retriever import ChunkHit, Retrieval
from govplatform.search.rerank import RankedHit


def test_weak_evidence_retries_at_most_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    obj = KnowledgeObject(
        knowledge_id="k1",
        title="照片同步",
        type=KnowledgeType.PROJECT_STANDARD,
        body="照片来源是 MediaStore",
        source="docs/photo.md",
        author=Agent(kind="codex", session_id="test"),
        authority_level=AuthorityLevel.PROJECT,
        content_hash="hash1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    hit = ChunkHit("c1", "k1", 1, (), obj.body, obj.source, obj.content_hash, 0.01)
    client = MagicMock()
    monkeypatch.setattr(pipeline, "elasticsearch_client", lambda: client)
    monkeypatch.setattr(pipeline, "require_ready_index", lambda *_args: "index")
    monkeypatch.setattr(pipeline, "retrieve", lambda *_args: Retrieval([hit], True))
    monkeypatch.setattr(pipeline, "rerank_hits", lambda *_args, **_kwargs: [RankedHit(hit, 0.1)])

    first = pipeline.search_chunks(
        query="没有依据的问题", index_objects=[obj], authorized_objects=[obj], limit=10, attempt=0
    )
    last = pipeline.search_chunks(
        query="第二次改写仍无依据",
        index_objects=[obj],
        authorized_objects=[obj],
        limit=10,
        attempt=2,
    )
    assert first.grade == "retry" and first.hits == []
    assert last.grade == "insufficient" and last.hits == []
    with pytest.raises(ValueError, match="between 0 and 2"):
        pipeline.search_chunks(
            query="第三次改写", index_objects=[obj], authorized_objects=[obj], limit=10, attempt=3
        )
    assert client.close.call_count == 2
