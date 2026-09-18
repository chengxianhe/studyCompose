from __future__ import annotations

import pytest

from govplatform.audit.store import list_audit_events
from govplatform.db.connection import get_connection
from govplatform.identity.models import Agent
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType
from govplatform.knowledge.sensitive import find_sensitive_reason, redact
from govplatform.knowledge.service import SensitiveContentError
from govplatform.search import service as search_service


@pytest.mark.parametrize(
    "body",
    [
        "联系电话 13812345678",
        "身份证 110101199003072316",
        "password=hunter2",
        "api_key: sk-abcdefghijklmnopqrst",
    ],
)
def test_propose_rejects_sensitive_body(body: str, claude_code_agent: Agent) -> None:
    with pytest.raises(SensitiveContentError):
        knowledge_service.propose(
            title="不该被写进去的知识",
            type=KnowledgeType.REFERENCE,
            body=body,
            source="test",
            authority_level=AuthorityLevel.REFERENCE,
            caller=claude_code_agent,
        )

    with get_connection() as conn:
        events = list_audit_events(conn)
    assert len(events) == 1
    assert events[0].action == "knowledge.propose.rejected"
    assert events[0].knowledge_id is None
    assert body not in events[0].request_json


def test_propose_rejects_sensitive_tags(claude_code_agent: Agent) -> None:
    with pytest.raises(SensitiveContentError):
        knowledge_service.propose(
            title="正常标题",
            type=KnowledgeType.REFERENCE,
            body="正常正文",
            source="test",
            authority_level=AuthorityLevel.REFERENCE,
            caller=claude_code_agent,
            tags=["token=abc123"],
        )

    with get_connection() as conn:
        events = list_audit_events(conn)
    assert len(events) == 1
    assert events[0].action == "knowledge.propose.rejected"


def test_propose_allows_clean_body(claude_code_agent: Agent) -> None:
    obj = knowledge_service.propose(
        title="正常知识",
        type=KnowledgeType.REFERENCE,
        body="这条正文完全不含敏感信息",
        source="test",
        authority_level=AuthorityLevel.REFERENCE,
        caller=claude_code_agent,
    )
    assert obj.body == "这条正文完全不含敏感信息"


def test_search_query_is_redacted_in_audit_log(claude_code_agent: Agent) -> None:
    search_service.search(query="手机号 13812345678 是谁的", caller=claude_code_agent)

    with get_connection() as conn:
        events = list_audit_events(conn)

    assert len(events) == 1
    assert "13812345678" not in events[0].request_json
    assert "[REDACTED]" in events[0].request_json


def test_find_sensitive_reason_and_redact_helpers() -> None:
    assert find_sensitive_reason("正常文本") is None
    assert find_sensitive_reason("我的手机号是 13812345678") == "手机号"
    assert redact("token=abc123") == "[REDACTED]"
