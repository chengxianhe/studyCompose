from __future__ import annotations

import pytest

from govplatform import embedding as embedding_module
from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType
from govplatform.search import service as search_service


def _propose_and_approve(*, title: str, body: str, agent: Agent, owner: Human) -> str:
    proposed = knowledge_service.propose(
        title=title,
        type=KnowledgeType.PROJECT_STANDARD,
        body=body,
        source="test",
        authority_level=AuthorityLevel.PROJECT,
        caller=agent,
    )
    knowledge_service.approve(knowledge_id=proposed.knowledge_id, caller=owner)
    return proposed.knowledge_id


def test_semantic_match_finds_result_with_no_literal_keyword_overlap(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    # 正文里出现的是"依赖"，完全没有"耦合"这两个字——纯 BM25 搜不到这条，
    # 混合检索要靠向量那条路径把它捞出来。
    dependency_id = _propose_and_approve(
        title="架构分层硬性规则",
        body="feature 模块不能直接依赖 data 模块，必须通过 domain 层的 UseCase",
        agent=claude_code_agent,
        owner=owner_human,
    )
    _propose_and_approve(
        title="设计系统间距 token",
        body="Spacing.lg 是 16dp，Spacing.xl 是 24dp，禁止在业务代码里内联 dp 数值",
        agent=claude_code_agent,
        owner=owner_human,
    )

    result = search_service.search(query="模块之间耦合太重怎么拆", caller=owner_human)

    assert result.results
    assert result.results[0].knowledge_id == dependency_id
    assert result.retrieval_mode == "hybrid"


def test_retrieval_mode_is_bm25_only_when_no_candidate_has_a_usable_embedding(
    claude_code_agent: Agent, owner_human: Human, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _broken_embed(text: str) -> bytes:
        raise RuntimeError("model unavailable")

    # propose 阶段模型是好的，正常存向量；只在 search 阶段把模型弄坏，
    # 模拟"库里有历史数据，但这次查询时模型不可用"这种情况。
    _propose_and_approve(
        title="任意一条知识",
        body="随便什么正文",
        agent=claude_code_agent,
        owner=owner_human,
    )
    monkeypatch.setattr(embedding_module, "embed", _broken_embed)

    result = search_service.search(query="任意一条知识", caller=owner_human)

    assert result.retrieval_mode == "bm25_only"
