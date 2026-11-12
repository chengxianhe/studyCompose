"""Exercise the installed MCP protocol against isolated knowledge and real local models."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest
from elasticsearch import NotFoundError
from mcp import Client, StdioServerParameters

from govplatform.identity.models import Agent, Human
from govplatform.ingest.__main__ import _active_objects
from govplatform.ingest.es_index import elasticsearch_client, sync_index
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType
from govplatform.search.service import SearchResponse


@pytest.mark.skipif(
    not os.environ.get("GOVPLAT_ES_URL"), reason="requires real local Elasticsearch"
)
async def test_stdio_search_evidence_rewrites_and_limit(
    codex_agent: Agent, owner_human: Human, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Human approval is synthetic test setup in conftest's temporary database only.
    alias = f"govplatform_test_{uuid.uuid4().hex}"
    monkeypatch.setenv("GOVPLAT_ES_INDEX_ALIAS", alias)
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    client = elasticsearch_client()
    try:
        obj = knowledge_service.propose(
            title="本地知识检索模型验证",
            type=KnowledgeType.REFERENCE,
            body="# 本地模型\n知识检索使用本地模型生成向量。\n## 验证\n断网检查模型文件摘要。",
            source="synthetic://local-model-check",
            authority_level=AuthorityLevel.REFERENCE,
            caller=codex_agent,
        )
        knowledge_service.approve(knowledge_id=obj.knowledge_id, caller=owner_human)
        sync_index(client, _active_objects())
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "govplatform.mcp_server.server"],
            cwd=str(Path(__file__).resolve().parents[1]),
            env=dict(os.environ),
        )
        async with Client(server, read_timeout_seconds=90) as mcp:
            catalog = await mcp.list_tools()
            assert "knowledge.search" in {tool.name for tool in catalog.tools}
            search_tool = next(tool for tool in catalog.tools if tool.name == "knowledge.search")
            description = search_tool.description or ""
            assert "pass 仅表示候选相关，不代表足以回答" in description
            assert "answer_assessment=not_assessed" in description
            assert "保留原问约束" in description

            # Fixed reformulations test the wire contract, not autonomous LLM rewriting.
            for attempt, query in enumerate(
                ("如何烘焙巧克力蛋糕", "巧克力蛋糕烘烤温度是多少", "蛋糕配方需要多少面粉")
            ):
                response = await mcp.call_tool(
                    "knowledge.search",
                    {"query": query, "attempt": attempt, "caller": codex_agent.model_dump()},
                )
                assert not response.is_error
                assert response.structured_content is not None
                assert response.structured_content["answer_assessment"] == "not_assessed"
                result = SearchResponse.model_validate(response.structured_content)
                assert result.retrieval_backend == "elasticsearch"
                assert result.retrieval_mode == "hybrid"
                assert result.relevance_grade == ("retry" if attempt < 2 else "insufficient")
                assert result.results == []
                assert result.attempt == attempt
                assert result.remaining_rewrites == 2 - attempt

            response = await mcp.call_tool(
                "knowledge.search",
                {
                    "query": "知识检索本地模型如何验证",
                    "attempt": 1,
                    "caller": codex_agent.model_dump(),
                },
            )
            assert not response.is_error
            assert response.structured_content is not None
            assert response.structured_content["answer_assessment"] == "not_assessed"
            result = SearchResponse.model_validate(response.structured_content)
            assert result.relevance_grade == "pass"
            assert result.retrieval_backend == "elasticsearch"
            assert result.results
            assert all(hit.knowledge_id == obj.knowledge_id for hit in result.results)
            assert all(hit.chunk_id and hit.source == obj.source for hit in result.results)
            assert any("摘要" in hit.snippet for hit in result.results)

            rejected = await mcp.call_tool(
                "knowledge.search",
                {"query": "第三次改写", "attempt": 3, "caller": codex_agent.model_dump()},
            )
            assert rejected.is_error

            # A rejected request must not break the connection or subsequent valid calls.
            valid = await mcp.call_tool(
                "knowledge.search",
                {"query": "知识检索本地模型如何验证", "caller": codex_agent.model_dump()},
            )
            assert not valid.is_error
            assert SearchResponse.model_validate(valid.structured_content).relevance_grade == "pass"
    finally:
        try:
            names = list(client.indices.get_alias(name=alias).keys())
        except NotFoundError:
            names = []
        for name in names:
            client.indices.delete(index=name)
        client.close()
