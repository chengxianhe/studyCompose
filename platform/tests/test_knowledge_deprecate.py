from __future__ import annotations

import pytest

from govplatform.identity.models import Agent, Human, PrincipalNotAllowedError
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeStatus, KnowledgeType
from govplatform.knowledge.service import KnowledgeStateError, SensitiveContentError
from govplatform.search import service as search_service


def _propose_and_approve(agent: Agent, owner: Human) -> str:
    proposed = knowledge_service.propose(
        title="过时的规则",
        type=KnowledgeType.PROJECT_STANDARD,
        body="唯一关键词是 deprecatetestkeyword",
        source="test",
        authority_level=AuthorityLevel.PROJECT,
        caller=agent,
    )
    knowledge_service.approve(knowledge_id=proposed.knowledge_id, caller=owner)
    return proposed.knowledge_id


def test_deprecate_takes_knowledge_off_search(claude_code_agent: Agent, owner_human: Human) -> None:
    knowledge_id = _propose_and_approve(claude_code_agent, owner_human)

    before = search_service.search(query="deprecatetestkeyword", caller=owner_human)
    assert any(r.knowledge_id == knowledge_id for r in before.results)

    deprecated = knowledge_service.deprecate(
        knowledge_id=knowledge_id, caller=owner_human, reason="规则已经被新规范取代"
    )
    assert deprecated.status == KnowledgeStatus.DEPRECATED

    after = search_service.search(query="deprecatetestkeyword", caller=owner_human)
    assert not any(r.knowledge_id == knowledge_id for r in after.results)


def test_deprecate_requires_human(claude_code_agent: Agent, owner_human: Human) -> None:
    knowledge_id = _propose_and_approve(claude_code_agent, owner_human)

    with pytest.raises(PrincipalNotAllowedError):
        knowledge_service.deprecate(
            knowledge_id=knowledge_id, caller=claude_code_agent, reason="AI 不该能自己下线知识"
        )


def test_deprecate_rejects_non_active_knowledge(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    proposed = knowledge_service.propose(
        title="还没审核的知识",
        type=KnowledgeType.REFERENCE,
        body="正文",
        source="test",
        authority_level=AuthorityLevel.REFERENCE,
        caller=claude_code_agent,
    )

    with pytest.raises(KnowledgeStateError):
        knowledge_service.deprecate(
            knowledge_id=proposed.knowledge_id, caller=owner_human, reason="还没生效就想下线"
        )


def test_deprecate_rejects_sensitive_reason(claude_code_agent: Agent, owner_human: Human) -> None:
    knowledge_id = _propose_and_approve(claude_code_agent, owner_human)

    with pytest.raises(SensitiveContentError):
        knowledge_service.deprecate(
            knowledge_id=knowledge_id, caller=owner_human, reason="联系电话 13812345678"
        )
