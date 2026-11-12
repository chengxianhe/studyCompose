"""Search relevance must not be serialized as a semantic answer assessment."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from govplatform import embedding
from govplatform.api.app import create_app
from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeObject, KnowledgeType
from govplatform.search import pipeline
from govplatform.search import service as search_service
from govplatform.search.es_retriever import ChunkHit
from govplatform.search.rerank import RankedHit
from govplatform.search.service import SearchResponse


def _model_unavailable(_text: str) -> bytes:
    raise RuntimeError("synthetic unavailable embedding model")


@pytest.fixture
def reimbursement(
    codex_agent: Agent, owner_human: Human, monkeypatch: pytest.MonkeyPatch
) -> KnowledgeObject:
    monkeypatch.setattr(embedding, "embed", _model_unavailable)
    proposed = knowledge_service.propose(
        title="合成报销凭证清单",
        type=KnowledgeType.REFERENCE,
        body="费用报销需要发票和付款凭证。清单未提供报销网站地址。",
        source="synthetic://answer-contract/reimbursement",
        authority_level=AuthorityLevel.REFERENCE,
        caller=codex_agent,
    )
    # conftest isolates every test in a temporary database; never production approval.
    return knowledge_service.approve(knowledge_id=proposed.knowledge_id, caller=owner_human)


@pytest.mark.parametrize(
    ("grade", "attempt", "rewrites"),
    [("pass", 0, 0), ("retry", 1, 1), ("insufficient", 2, 0), ("unavailable", 0, 0)],
)
def test_service_does_not_assess_answer_from_relevance(
    grade: pipeline.Grade,
    attempt: int,
    rewrites: int,
    reimbursement: KnowledgeObject,
    codex_agent: Agent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    obj = reimbursement
    hit = ChunkHit(
        "synthetic-chunk", obj.knowledge_id, obj.version, (), obj.body,
        obj.source, obj.content_hash, 0.03,
    )
    hits = [RankedHit(hit, 0.999)] if grade in ("pass", "unavailable") else []
    indexed = pipeline.PipelineResult(hits, grade, True, grade != "unavailable")
    monkeypatch.setattr(pipeline, "enabled", lambda: True)
    monkeypatch.setattr(pipeline, "search_chunks", lambda **_kwargs: indexed)

    response = search_service.search(
        query="报销网站的具体 URL 是什么？", caller=codex_agent, attempt=attempt
    )
    wire = json.loads(response.model_dump_json())
    assert response.retrieval_backend == "elasticsearch"
    assert response.relevance_grade == grade
    assert response.attempt == attempt
    assert response.remaining_rewrites == rewrites
    assert wire["answer_assessment"] == "not_assessed"
    assert bool(response.results) == bool(hits)
    if hits:
        assert wire["results"][0]["snippet"] == obj.body
        assert wire["results"][0]["version"] == obj.version
        assert wire["results"][0]["source"] == obj.source


@pytest.mark.parametrize("es_fails", [False, True])
def test_sqlite_and_http_do_not_infer_answerability_on_fallback(
    es_fails: bool,
    reimbursement: KnowledgeObject,
    codex_agent: Agent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_pipeline(**_kwargs: object) -> pipeline.PipelineResult:
        raise OSError("synthetic Elasticsearch failure")

    monkeypatch.setattr(pipeline, "enabled", lambda: es_fails)
    monkeypatch.setattr(pipeline, "search_chunks", fail_pipeline)
    response = TestClient(create_app()).post(
        "/knowledge/search",
        json={"query": "报销凭证", "caller": codex_agent.model_dump()},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["retrieval_backend"] == "sqlite_fallback"
    assert result["retrieval_mode"] == "bm25_only"
    assert result["relevance_grade"] == "unavailable"
    assert result["answer_assessment"] == "not_assessed"
    assert result["results"][0]["knowledge_id"] == reimbursement.knowledge_id


def test_empty_search_is_not_a_semantic_insufficiency_assessment(
    codex_agent: Agent, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline, "enabled", lambda: False)
    monkeypatch.setattr(embedding, "embed", _model_unavailable)
    result = search_service.search(query="具体报销网址", caller=codex_agent)
    assert result.results == []
    assert result.relevance_grade == "unavailable"
    assert json.loads(result.model_dump_json())["answer_assessment"] == "not_assessed"


def test_response_contract_reads_legacy_payload_but_rejects_semantic_claim() -> None:
    legacy = {"query": "报销网址", "results": [], "retrieval_mode": "bm25_only"}
    result = SearchResponse.model_validate(legacy)
    assert json.loads(result.model_dump_json())["answer_assessment"] == "not_assessed"
    with pytest.raises(ValidationError, match="answer_assessment"):
        SearchResponse.model_validate({**legacy, "answer_assessment": "supported"})
    assessment = SearchResponse.model_json_schema()["properties"]["answer_assessment"]
    assert assessment["const"] == "not_assessed"
