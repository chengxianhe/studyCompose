from __future__ import annotations

import pytest

from govplatform.audit.store import list_audit_events
from govplatform.db.connection import get_connection
from govplatform.identity.models import Agent, Human, PrincipalNotAllowedError
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType
from govplatform.search import service as search_service


def test_distinct_agent_identities_produce_distinguishable_audit_rows(
    claude_code_agent: Agent, codex_agent: Agent
) -> None:
    search_service.search(query="anything", caller=claude_code_agent)
    search_service.search(query="anything", caller=codex_agent)

    with get_connection() as conn:
        events = list_audit_events(conn)

    search_events = [e for e in events if e.action == "knowledge.search"]
    assert len(search_events) == 2
    principal_ids = {e.principal_id for e in search_events}
    session_ids = {e.session_id for e in search_events}
    assert principal_ids == {"claude-code", "codex"}
    assert session_ids == {"test-session-claude", "test-session-codex"}


def test_unlisted_agent_kind_is_rejected_before_any_write(owner_human: Human) -> None:
    with pytest.raises(PrincipalNotAllowedError):
        knowledge_service.propose(
            title="should not be written",
            type=KnowledgeType.REFERENCE,
            body="x",
            source="test",
            authority_level=AuthorityLevel.REFERENCE,
            caller=Agent(kind="gemini-cli", session_id="untrusted"),
        )

    with get_connection() as conn:
        assert list_audit_events(conn) == []


def test_non_owner_human_is_rejected(claude_code_agent: Agent) -> None:
    proposed = knowledge_service.propose(
        title="owned by someone else",
        type=KnowledgeType.REFERENCE,
        body="x",
        source="test",
        authority_level=AuthorityLevel.REFERENCE,
        caller=claude_code_agent,
    )
    with pytest.raises(PrincipalNotAllowedError):
        knowledge_service.approve(
            knowledge_id=proposed.knowledge_id, caller=Human(id="someone-else@example.com")
        )
