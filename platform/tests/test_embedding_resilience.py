from __future__ import annotations

from datetime import UTC, datetime

import pytest

from govplatform import embedding as embedding_module
from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import (
    AuthorityLevel,
    KnowledgeObject,
    KnowledgeStatus,
    KnowledgeType,
)
from govplatform.knowledge.store import StoredEmbedding
from govplatform.search import hybrid
from govplatform.search import service as search_service


def test_propose_succeeds_even_if_embedding_model_fails(
    claude_code_agent: Agent, owner_human: Human, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _broken_embed(text: str) -> bytes:
        raise RuntimeError("model failed to load")

    monkeypatch.setattr(embedding_module, "embed", _broken_embed)

    proposed = knowledge_service.propose(
        title="向量模型挂了也不该阻断提交",
        type=KnowledgeType.REFERENCE,
        body="这条知识在向量模型失败的情况下依然要能提交成功",
        source="test",
        authority_level=AuthorityLevel.REFERENCE,
        caller=claude_code_agent,
    )
    assert proposed.status == KnowledgeStatus.IN_REVIEW

    knowledge_service.approve(knowledge_id=proposed.knowledge_id, caller=owner_human)

    # 没有向量也应该能靠 BM25 搜到（关键词命中）。
    result = search_service.search(query="向量模型挂了也不该阻断提交", caller=owner_human)
    assert any(r.knowledge_id == proposed.knowledge_id for r in result.results)


def test_hybrid_rank_skips_embeddings_from_a_different_model() -> None:
    query = "这段查询词跟下面知识的标题正文一个字都不重合"

    # 故意把"存的向量"直接算成查询词本身——如果向量比较真的参与了，
    # 余弦相似度会是 1.0，稳赢。但这个向量标的是一个已经不再使用的模型
    # 名字，理应被跳过。知识本身的标题/正文跟查询词没有任何字面重合，
    # BM25 那条路也找不到它——如果模型校验没生效，这个测试就会因为向量
    # 比对"作弊"把它找出来而失败；校验生效的话应该什么都搜不到。
    stale_vector_pretending_to_match = embedding_module.embed(query)
    now = datetime.now(UTC)
    obj = KnowledgeObject(
        knowledge_id="k1",
        title="架构分层的一条硬性规则",
        type=KnowledgeType.REFERENCE,
        body="feature 模块禁止直接依赖 data 模块的任何类",
        source="test",
        author=Agent(kind="claude-code", session_id="s"),
        authority_level=AuthorityLevel.REFERENCE,
        content_hash="hash",
        created_at=now,
        updated_at=now,
    )
    candidates = [
        (obj, StoredEmbedding(stale_vector_pretending_to_match, "some-retired-model-name"))
    ]

    ranked = hybrid.rank(candidates, query=query, limit=10)

    assert ranked.results == []
    assert ranked.used_vector_search is False
