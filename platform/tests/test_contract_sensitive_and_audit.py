from __future__ import annotations

import pytest

from govplatform.audit.store import list_audit_events
from govplatform.contract import service as contract_service
from govplatform.contract.service import SensitiveContentError
from govplatform.db.connection import get_connection
from govplatform.identity.models import Agent, Human


def test_create_rejects_sensitive_content_in_goal(claude_code_agent: Agent) -> None:
    with pytest.raises(SensitiveContentError):
        contract_service.create(
            title="标题正常",
            goal="联系电话 13812345678",
            scope="范围",
            caller=claude_code_agent,
        )

    with get_connection() as conn:
        events = list_audit_events(conn)
    assert len(events) == 1
    assert events[0].action == "contract.create.rejected"


def test_get_writes_an_audit_event(claude_code_agent: Agent, owner_human: Human) -> None:
    contract = contract_service.create(
        title="正常契约",
        goal="目标",
        scope="范围",
        caller=claude_code_agent,
    )

    contract_service.get(contract.contract_id, caller=owner_human)

    with get_connection() as conn:
        events = list_audit_events(conn)
    get_events = [e for e in events if e.action == "contract.get"]
    assert len(get_events) == 1
    assert get_events[0].principal_id == owner_human.id
