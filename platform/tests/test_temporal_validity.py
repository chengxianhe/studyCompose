from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType
from govplatform.knowledge.service import InvalidTimeRangeError
from govplatform.search import service as search_service

_NOW = datetime.now(UTC)


def _propose_and_approve(
    *,
    title: str,
    body: str,
    agent: Agent,
    owner: Human,
    effective_at: datetime | None = None,
    expire_at: datetime | None = None,
) -> str:
    proposed = knowledge_service.propose(
        title=title,
        type=KnowledgeType.REFERENCE,
        body=body,
        source="test",
        authority_level=AuthorityLevel.REFERENCE,
        caller=agent,
        effective_at=effective_at,
        expire_at=expire_at,
    )
    knowledge_service.approve(knowledge_id=proposed.knowledge_id, caller=owner)
    return proposed.knowledge_id


def test_expired_knowledge_is_excluded_even_if_active(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    _propose_and_approve(
        title="已经过期的规则",
        body="这条规则唯一关键词是 expiretestkeyword",
        agent=claude_code_agent,
        owner=owner_human,
        expire_at=_NOW - timedelta(days=1),
    )

    result = search_service.search(query="expiretestkeyword", caller=owner_human)

    assert result.results == []


def test_not_yet_effective_knowledge_is_excluded(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    _propose_and_approve(
        title="还没到生效时间的规则",
        body="这条规则唯一关键词是 futuretestkeyword",
        agent=claude_code_agent,
        owner=owner_human,
        effective_at=_NOW + timedelta(days=30),
    )

    result = search_service.search(query="futuretestkeyword", caller=owner_human)

    assert result.results == []


def test_currently_valid_knowledge_is_found(claude_code_agent: Agent, owner_human: Human) -> None:
    knowledge_id = _propose_and_approve(
        title="现在生效中的规则",
        body="这条规则唯一关键词是 validtestkeyword",
        agent=claude_code_agent,
        owner=owner_human,
        effective_at=_NOW - timedelta(days=1),
        expire_at=_NOW + timedelta(days=30),
    )

    result = search_service.search(query="validtestkeyword", caller=owner_human)

    assert any(r.knowledge_id == knowledge_id for r in result.results)


def test_naive_datetime_does_not_crash(claude_code_agent: Agent, owner_human: Human) -> None:
    # 不带时区的时间也不能让写入或搜索直接崩溃。
    naive_future = datetime.now() + timedelta(days=30)
    knowledge_id = _propose_and_approve(
        title="用不带时区的时间设置生效期",
        body="这条规则唯一关键词是 naivetestkeyword",
        agent=claude_code_agent,
        owner=owner_human,
        effective_at=naive_future,
    )

    # effective_at 在未来，不管有没有时区都应该被排除。
    result = search_service.search(query="naivetestkeyword", caller=owner_human)
    assert not any(r.knowledge_id == knowledge_id for r in result.results)


def test_propose_rejects_expire_at_before_effective_at(claude_code_agent: Agent) -> None:
    with pytest.raises(InvalidTimeRangeError):
        knowledge_service.propose(
            title="失效比生效还早，永远搜不到",
            type=KnowledgeType.REFERENCE,
            body="这条知识的有效期区间是反的",
            source="test",
            authority_level=AuthorityLevel.REFERENCE,
            caller=claude_code_agent,
            effective_at=_NOW + timedelta(days=10),
            expire_at=_NOW + timedelta(days=5),
        )


def test_propose_rejects_expire_at_equal_to_effective_at(claude_code_agent: Agent) -> None:
    same_instant = _NOW + timedelta(days=10)
    with pytest.raises(InvalidTimeRangeError):
        knowledge_service.propose(
            title="生效和失效是同一时刻，有效期区间为空",
            type=KnowledgeType.REFERENCE,
            body="这条知识的有效期长度是零",
            source="test",
            authority_level=AuthorityLevel.REFERENCE,
            caller=claude_code_agent,
            effective_at=same_instant,
            expire_at=same_instant,
        )
