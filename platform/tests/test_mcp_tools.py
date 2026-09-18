from __future__ import annotations

from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType
from govplatform.mcp_server.server import knowledge_propose, knowledge_search


async def test_mcp_propose_and_search_round_trip(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    proposed = await knowledge_propose(
        title="MCP round trip note",
        type=KnowledgeType.REFERENCE,
        body="mcp propose tool writes an in_review object",
        source="test",
        authority_level=AuthorityLevel.REFERENCE,
        caller=claude_code_agent,
    )
    assert proposed.status.value == "in_review"

    knowledge_service.approve(knowledge_id=proposed.knowledge_id, caller=owner_human)

    response = await knowledge_search(query="mcp propose tool", caller=owner_human)
    assert any(r.knowledge_id == proposed.knowledge_id for r in response.results)
