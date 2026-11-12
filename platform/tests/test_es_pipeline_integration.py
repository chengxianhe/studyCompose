"""Run explicitly with GOVPLAT_ES_URL against a disposable local ES instance."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from elasticsearch import NotFoundError
from fastapi.testclient import TestClient

from govplatform.api.app import create_app
from govplatform.identity.models import Agent, Human
from govplatform.ingest.__main__ import _active_objects
from govplatform.ingest.es_index import elasticsearch_client, index_alias, sync_index
from govplatform.ingest.health import diagnose
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType
from govplatform.mcp_server.server import knowledge_search
from govplatform.search.service import search


@pytest.mark.skipif(
    not os.environ.get("GOVPLAT_ES_URL"), reason="requires real local Elasticsearch"
)
def test_approved_chunks_are_ranked_and_lifecycle_changes_rebuild_index(
    claude_code_agent: Agent, owner_human: Human, monkeypatch: pytest.MonkeyPatch
) -> None:
    alias = f"govplatform_test_{uuid.uuid4().hex}"
    monkeypatch.setenv("GOVPLAT_ES_INDEX_ALIAS", alias)
    client = elasticsearch_client()
    try:
        approved = knowledge_service.propose(
            title="知识检索部署",
            type=KnowledgeType.PROJECT_STANDARD,
            body="# 本地模型\n知识检索使用本地模型生成向量。\n## 验证\n断网检查模型文件摘要。",
            source="docs/search.md",
            authority_level=AuthorityLevel.PROJECT,
            caller=claude_code_agent,
        )
        pending = knowledge_service.propose(
            title="未批准的知识检索部署",
            type=KnowledgeType.PROJECT_STANDARD,
            body="未批准的知识不能用于检索答案。",
            source="docs/pending.md",
            authority_level=AuthorityLevel.PROJECT,
            caller=claude_code_agent,
        )
        expired = knowledge_service.propose(
            title="已过期的知识检索部署",
            type=KnowledgeType.PROJECT_STANDARD,
            body="已过期的知识不能用于检索答案。",
            source="docs/expired.md",
            authority_level=AuthorityLevel.PROJECT,
            caller=claude_code_agent,
            effective_at=datetime.now(UTC) - timedelta(days=2),
            expire_at=datetime.now(UTC) - timedelta(days=1),
        )
        knowledge_service.approve(knowledge_id=approved.knowledge_id, caller=owner_human)
        knowledge_service.approve(knowledge_id=expired.knowledge_id, caller=owner_human)

        before_sync = search(query="知识检索本地模型如何验证", caller=owner_human)
        assert before_sync.retrieval_backend == "sqlite_fallback"
        sync_index(client, _active_objects())
        assert diagnose(client, _active_objects())["ready"] is True
        first = search(query="知识检索本地模型如何验证", caller=owner_human)
        assert first.retrieval_backend == "elasticsearch"
        assert first.retrieval_mode == "hybrid"
        assert first.relevance_grade == "pass"
        assert first.results
        assert all(result.knowledge_id == approved.knowledge_id for result in first.results)
        assert all(result.chunk_id for result in first.results)
        assert pending.knowledge_id not in {result.knowledge_id for result in first.results}
        assert expired.knowledge_id not in {result.knowledge_id for result in first.results}
        assert client.count(index=index_alias())["count"] == 2
        through_mcp = asyncio.run(
            knowledge_search(query="知识检索本地模型如何验证", caller=owner_human, attempt=0)
        )
        assert through_mcp.retrieval_backend == "elasticsearch"
        through_http = TestClient(create_app()).post(
            "/knowledge/search",
            json={
                "query": "知识检索本地模型如何验证",
                "attempt": 0,
                "caller": {"principal_type": "human", "id": owner_human.id},
            },
        )
        assert through_http.status_code == 200
        assert through_http.json()["retrieval_backend"] == "elasticsearch"
        initial_index = next(iter(client.indices.get_alias(name=index_alias())))
        search(query="知识检索本地模型如何验证", caller=owner_human)
        assert next(iter(client.indices.get_alias(name=index_alias()))) == initial_index

        knowledge_service.deprecate(
            knowledge_id=approved.knowledge_id,
            reason="集成测试下线",
            caller=owner_human,
        )
        sync_index(client, _active_objects())
        after = search(query="知识检索本地模型如何验证", caller=owner_human)
        assert after.retrieval_backend == "elasticsearch"
        assert after.results == []
        assert after.relevance_grade == "retry"
        assert next(iter(client.indices.get_alias(name=index_alias()))) != initial_index
        assert not client.indices.exists(index=initial_index)
    finally:
        try:
            names = list(client.indices.get_alias(name=alias).keys())
        except NotFoundError:
            names = []
        for name in names:
            client.indices.delete(index=name)
        client.close()
