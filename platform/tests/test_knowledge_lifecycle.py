from __future__ import annotations

from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeStatus, KnowledgeType
from govplatform.search import service as search_service


def test_propose_then_approve_then_search_finds_active_object(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    proposed = knowledge_service.propose(
        title="Konsist enforces feature/data boundary",
        type=KnowledgeType.PROJECT_STANDARD,
        body="feature modules must not import data package classes directly",
        source="CLAUDE.md#硬性规则",
        authority_level=AuthorityLevel.PROJECT,
        caller=claude_code_agent,
    )
    assert proposed.status == KnowledgeStatus.IN_REVIEW

    not_yet_visible = search_service.search(
        query="Konsist feature data boundary", caller=claude_code_agent
    )
    assert not_yet_visible.results == []

    approved = knowledge_service.approve(knowledge_id=proposed.knowledge_id, caller=owner_human)
    assert approved.status == KnowledgeStatus.ACTIVE
    assert approved.owner == owner_human.id

    found = search_service.search(query="Konsist feature data boundary", caller=owner_human)
    assert len(found.results) == 1
    result = found.results[0]
    assert result.knowledge_id == proposed.knowledge_id
    assert result.source == "CLAUDE.md#硬性规则"
    assert result.version == 1
    assert result.authority_level == AuthorityLevel.PROJECT
