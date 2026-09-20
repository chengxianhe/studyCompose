from __future__ import annotations

from fastapi.testclient import TestClient

from govplatform.api.app import create_app


def test_approve_requires_human_owner_and_flips_status() -> None:
    client = TestClient(create_app())

    propose_response = client.post(
        "/knowledge/propose",
        json={
            "title": "API loop note",
            "type": "reference",
            "body": "api propose to approve to search round trip",
            "source": "test",
            "authority_level": "reference",
            "caller": {"principal_type": "agent", "kind": "claude-code", "session_id": "api-test"},
        },
    )
    assert propose_response.status_code == 200
    knowledge_id = propose_response.json()["knowledge_id"]

    agent_approve = client.post(
        f"/knowledge/{knowledge_id}/approve",
        json={
            "caller": {"principal_type": "agent", "kind": "claude-code", "session_id": "api-test"}
        },
    )
    assert agent_approve.status_code == 403

    owner_approve = client.post(
        f"/knowledge/{knowledge_id}/approve",
        json={"caller": {"principal_type": "human", "id": "chengxianhe0@gmail.com"}},
    )
    assert owner_approve.status_code == 200
    assert owner_approve.json()["status"] == "active"

    search_response = client.post(
        "/knowledge/search",
        json={
            "query": "api propose approve search",
            "caller": {"principal_type": "human", "id": "chengxianhe0@gmail.com"},
        },
    )
    assert search_response.status_code == 200
    assert any(r["knowledge_id"] == knowledge_id for r in search_response.json()["results"])

    agent_deprecate = client.post(
        f"/knowledge/{knowledge_id}/deprecate",
        json={
            "caller": {"principal_type": "agent", "kind": "claude-code", "session_id": "api-test"},
            "reason": "AI 不该能自己下线知识",
        },
    )
    assert agent_deprecate.status_code == 403

    owner_deprecate = client.post(
        f"/knowledge/{knowledge_id}/deprecate",
        json={
            "caller": {"principal_type": "human", "id": "chengxianhe0@gmail.com"},
            "reason": "已经被新规则取代",
        },
    )
    assert owner_deprecate.status_code == 200
    assert owner_deprecate.json()["status"] == "deprecated"

    search_after_deprecate = client.post(
        "/knowledge/search",
        json={
            "query": "api propose approve search",
            "caller": {"principal_type": "human", "id": "chengxianhe0@gmail.com"},
        },
    )
    assert not any(
        r["knowledge_id"] == knowledge_id for r in search_after_deprecate.json()["results"]
    )
