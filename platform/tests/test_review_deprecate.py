import re
from pathlib import Path

from fastapi.testclient import TestClient

from govplatform.config import db_path
from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeStatus, KnowledgeType
from govplatform.review.app import create_review_app
from govplatform.search.service import search


def test_deprecate_requires_reason_and_removes_search_result(
    codex_agent: Agent,
    owner_human: Human,
    tmp_path: Path,
) -> None:
    obj = service.propose(
        title="过时测试规则",
        type=KnowledgeType.REFERENCE,
        body="旧规则仅用于测试",
        source="test",
        authority_level=AuthorityLevel.REFERENCE,
        caller=codex_agent,
    )
    service.approve(knowledge_id=obj.knowledge_id, caller=owner_human)
    action = f"/actions/deprecate/{obj.knowledge_id}"
    with TestClient(
        create_review_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 1)
    ) as client:
        page = client.get(f"/knowledge/{obj.knowledge_id}").text
        fields = dict(re.findall(r'name="([^"]+)" value="([^"]+)"', page))
        assert (
            client.post(
                action, data={**fields, "reason": "过时"}, headers={"Origin": "https://evil.test"}
            ).status_code
            == 403
        )
        assert client.post(action, data={**fields, "reason": " "}).status_code == 409
        page = client.get(f"/knowledge/{obj.knowledge_id}").text
        fields = dict(re.findall(r'name="([^"]+)" value="([^"]+)"', page))
        assert (
            client.post(
                action, data={**fields, "reason": "新要求已取代"}, follow_redirects=False
            ).status_code
            == 303
        )
        assert client.post(action, data={**fields, "reason": "再次提交"}).status_code == 409
    current = service.get(obj.knowledge_id)
    assert current is not None and current.status == KnowledgeStatus.DEPRECATED
    assert search(query="过时测试规则", caller=codex_agent).results == []
    assert list((db_path().parent / "backups").glob("*/manifest.json"))
