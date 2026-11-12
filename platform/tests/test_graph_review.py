from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from graph_support import link, seed

from govplatform.config import db_path
from govplatform.graph import query_service
from govplatform.graph.models import ReviewSnapshot
from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service as knowledge
from govplatform.review.app import create_review_app


def _fields(page: str, action: str) -> dict[str, str]:
    body = re.search(
        r'<form method="post" action="' + re.escape(action) + r'">(.*?)</form>', page, re.S
    )
    assert body
    return dict(re.findall(r'name="([^"]+)" value="([^"]+)"', body[1]))


def test_review_protection_snapshot_replay_backup_and_html_escape(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch)
    obj = link(case, codex_agent)
    action = f"/graph/actions/approve/{obj.relation_id}"
    url = f"/graph/relations/{obj.relation_id}"
    with TestClient(
        create_review_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 1)
    ) as client:
        assert client.get("/graph").status_code == 200
        assert client.get("/graph/sources").status_code == 200
        assert client.get(f"/graph/sources/{case.source.source_id}").status_code == 200
        fields = _fields(client.get(url).text, action)
        assert (
            client.post(action, data=fields, headers={"Origin": "https://evil.test"}).status_code
            == 403
        )
        assert client.post(action, data={**fields, "csrf": "bad"}).status_code == 403
        assert client.post(action, data=fields, follow_redirects=False).status_code == 303
        assert client.post(action, data=fields).status_code == 409
        result = query_service.get(key=obj.relation_id, kind="relation", caller=codex_agent)
        assert isinstance(result, ReviewSnapshot) and result.relation.status == "active"
        revoke = f"/graph/actions/revoke/{obj.relation_id}"
        fields = _fields(client.get(url).text, revoke)
        assert (
            client.post(
                revoke,
                data={**fields, "reason": "<script>alert(1)</script>"},
                follow_redirects=False,
            ).status_code
            == 303
        )
        page = client.get(url).text
        assert "&lt;script&gt;" in page and "<script>" not in page
    assert len(list((db_path().parent / "backups").glob("*/manifest.json"))) == 2


def test_review_refuses_stale_endpoint_and_nonlocal_client(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch)
    obj = link(case, codex_agent)
    action = f"/graph/actions/approve/{obj.relation_id}"
    app = create_review_app()
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 1)) as client:
        fields = _fields(client.get(f"/graph/relations/{obj.relation_id}").text, action)
        knowledge.deprecate(knowledge_id=case.old.knowledge_id, caller=owner_human, reason="已过期")
        assert client.post(action, data=fields).status_code == 409
    with TestClient(app, base_url="http://127.0.0.1", client=("192.0.2.1", 1)) as client:
        assert client.get("/graph").status_code == 403
