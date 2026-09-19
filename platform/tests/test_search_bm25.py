from __future__ import annotations

from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType
from govplatform.search import service as search_service


def _propose_and_approve(*, title: str, body: str, agent: Agent, owner: Human) -> str:
    proposed = knowledge_service.propose(
        title=title,
        type=KnowledgeType.REFERENCE,
        body=body,
        source="test",
        authority_level=AuthorityLevel.REFERENCE,
        caller=agent,
    )
    knowledge_service.approve(knowledge_id=proposed.knowledge_id, caller=owner)
    return proposed.knowledge_id


def test_relevant_result_ranks_above_unrelated(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    target_id = _propose_and_approve(
        title="Retrofit interceptor retry policy",
        body="Retrofit client retries on 5xx with exponential backoff",
        agent=claude_code_agent,
        owner=owner_human,
    )
    _propose_and_approve(
        title="Compose spacing tokens",
        body="Spacing.lg is 16dp, Spacing.xl is 24dp",
        agent=claude_code_agent,
        owner=owner_human,
    )

    result = search_service.search(query="Retrofit retry backoff", caller=owner_human)

    # 混合检索不再保证完全不相关的文档被硬性过滤掉——向量那条路径只做相对
    # 排序，不设绝对阈值（原因见 platform/README.md）。这里只断言真正相关
    # 的结果排第一、分数明显更高，不再断言"只有一条结果"。
    assert result.results[0].knowledge_id == target_id
    if len(result.results) > 1:
        assert result.results[0].score > result.results[1].score


def test_search_ignores_in_review_objects(claude_code_agent: Agent, owner_human: Human) -> None:
    knowledge_service.propose(
        title="Draft note about pagination",
        type=KnowledgeType.EXPERIENCE,
        body="pagination cursor must be opaque",
        source="test",
        authority_level=AuthorityLevel.REFERENCE,
        caller=claude_code_agent,
    )

    result = search_service.search(query="pagination cursor opaque", caller=owner_human)

    assert result.results == []
