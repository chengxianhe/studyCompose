from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from govplatform import embedding
from govplatform.api.app import create_app
from govplatform.config import db_path
from govplatform.db.connection import get_connection
from govplatform.identity.models import Agent, PrincipalNotAllowedError
from govplatform.knowledge import service
from govplatform.knowledge.models import (
    AuthorityLevel,
    KnowledgeObject,
    KnowledgeStatus,
    KnowledgeType,
)
from govplatform.knowledge.query_service import get_knowledge, list_knowledge
from govplatform.review.app import create_review_app
from govplatform.search.service import search


@pytest.fixture
def candidate(monkeypatch: pytest.MonkeyPatch, codex_agent: Agent) -> KnowledgeObject:
    def unavailable(text: str) -> bytes:
        raise RuntimeError("offline test")

    monkeypatch.setattr(embedding, "embed", unavailable)
    return service.propose(
        title="知识闭环 <script>alert(1)</script>",
        type=KnowledgeType.PROJECT_STANDARD,
        body="验收证据需关联任务记录",
        source="test fixture",
        authority_level=AuthorityLevel.PROJECT,
        caller=codex_agent,
    )


def form_fields(html: str) -> dict[str, str]:
    return dict(re.findall(r'name="([^"]+)" value="([^"]+)"', html))


def test_queries_audited_and_pending_not_searchable(
    candidate: KnowledgeObject, codex_agent: Agent
) -> None:
    page = list_knowledge(caller=codex_agent, limit=1)
    assert page.total == 1 and page.items == [candidate]
    assert list_knowledge(caller=codex_agent, offset=1).items == []
    assert get_knowledge(knowledge_id=candidate.knowledge_id, caller=codex_agent) == candidate
    assert search(query="验收证据", caller=codex_agent).results == []
    with get_connection() as conn:
        actions = {row[0] for row in conn.execute("SELECT action FROM audit_events")}
    assert {"knowledge.list", "knowledge.get"} <= actions
    with pytest.raises(PrincipalNotAllowedError):
        list_knowledge(caller=Agent(kind="unknown", session_id="bad"))
    with pytest.raises(ValueError):
        list_knowledge(caller=codex_agent, limit=101)


def test_http_and_mcp_queries(candidate: KnowledgeObject, codex_agent: Agent) -> None:
    with TestClient(create_app()) as client:
        assert (
            client.post("/knowledge/list", json={"caller": codex_agent.model_dump()}).json()[
                "total"
            ]
            == 1
        )
        assert (
            client.post(
                "/knowledge/list",
                json={
                    "caller": codex_agent.model_dump(),
                    "offset": -1,
                },
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/knowledge/list",
                json={
                    "caller": {"principal_type": "agent", "kind": "bad", "session_id": "bad"},
                },
            ).status_code
            == 403
        )


@pytest.mark.asyncio
async def test_mcp_tool_surface(candidate: KnowledgeObject, codex_agent: Agent) -> None:
    from govplatform.mcp_server.server import knowledge_get, knowledge_list, mcp

    assert (await knowledge_list(codex_agent)).total == 1
    assert await knowledge_get(candidate.knowledge_id, codex_agent) == candidate
    names = {tool.name for tool in await mcp.list_tools()}
    assert {"knowledge.list", "knowledge.get", "knowledge.search", "knowledge.propose"} <= names
    assert "knowledge.approve" not in names and "contract.freeze" not in names


def test_human_review_backup_and_active_search(
    candidate: KnowledgeObject, codex_agent: Agent, tmp_path: Path
) -> None:
    app = create_review_app()
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 123)) as client:
        page = client.get(f"/knowledge/{candidate.knowledge_id}")
        assert "<script>alert" not in page.text and "&lt;script&gt;" in page.text
        assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
        fields = form_fields(page.text)
        action = f"/actions/approve/{candidate.knowledge_id}"
        assert (
            client.post(action, data=fields, headers={"Origin": "https://evil.test"}).status_code
            == 403
        )
        assert client.post(action, data={"csrf": "bad"}).status_code == 403
        assert client.post(action, data={**fields, "snapshot": "stale"}).status_code == 409
        response = client.post(action, data=fields, follow_redirects=False)
        assert response.status_code == 303
        approved = service.get(candidate.knowledge_id)
        assert approved is not None and approved.status == KnowledgeStatus.ACTIVE
        assert (
            search(query="验收证据", caller=codex_agent).results[0].knowledge_id
            == candidate.knowledge_id
        )
        assert client.post(action, data=fields).status_code == 409
        assert client.post("/knowledge/x/approve", json={}).status_code == 404
    snapshots = list((db_path().parent / "backups").iterdir())
    assert len(snapshots) == 1
    from govplatform.backup import restore_backup

    restored = tmp_path / "restored.sqlite"
    assert restore_backup(snapshots[0], restored)["knowledge_objects"] == 1
    import sqlite3

    with sqlite3.connect(restored) as conn:
        assert conn.execute("SELECT status FROM knowledge_objects").fetchone()[0] == "in_review"


def test_review_rejects_remote_and_dns_rebinding() -> None:
    app = create_review_app()
    with TestClient(app, base_url="http://127.0.0.1", client=("192.0.2.1", 123)) as client:
        assert client.get("/").status_code == 403
    with TestClient(app, base_url="http://evil.test", client=("127.0.0.1", 123)) as client:
        assert client.get("/").status_code == 400


def test_agent_cannot_approve(candidate: KnowledgeObject, codex_agent: Agent) -> None:
    with pytest.raises(PrincipalNotAllowedError):
        service.approve(knowledge_id=candidate.knowledge_id, caller=codex_agent)
