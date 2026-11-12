from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

from elasticsearch import ApiError, TransportError
from pydantic import BaseModel, Field

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.db.connection import get_connection
from govplatform.identity.models import Human, Principal, resolve_principal
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge import store as knowledge_store
from govplatform.knowledge.models import AuthorityLevel, KnowledgeStatus, KnowledgeType
from govplatform.knowledge.sensitive import redact
from govplatform.search import hybrid, pipeline


class SearchResult(BaseModel):
    knowledge_id: str
    title: str
    snippet: str
    score: float
    source: str
    version: int
    authority_level: AuthorityLevel
    status: KnowledgeStatus
    chunk_id: str | None = None
    heading_path: list[str] | None = None
    retrieval_score: float | None = None
    relevance_score: float | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    # "hybrid" = BM25+向量都参与了这次排序；"bm25_only" = 向量那一路没有
    # 真正贡献结果（模型失败，或者候选里没有能比的向量）——调用方能看出
    # 这次结果是不是缺了语义检索这条证据链，不用去猜。
    retrieval_mode: Literal["hybrid", "bm25_only"]
    retrieval_backend: Literal["elasticsearch", "sqlite_fallback"] = "sqlite_fallback"
    relevance_grade: Literal["pass", "retry", "insufficient", "unavailable"] = "unavailable"
    answer_assessment: Literal["not_assessed"] = Field(
        default="not_assessed",
        description="平台未评估答案充分性；相关性 pass 仅表示候选相关，宿主须按原问核对来源证据。",
    )
    attempt: int = 0
    remaining_rewrites: int = 0


def _principal_type_and_id(principal: Principal) -> tuple[str, str, str | None]:
    if isinstance(principal, Human):
        return "human", principal.id, None
    return "agent", principal.kind, principal.session_id


def search(
    *,
    query: str,
    caller: Principal,
    knowledge_type: KnowledgeType | None = None,
    limit: int = 10,
    attempt: int = 0,
) -> SearchResponse:
    if not 0 <= attempt <= 2:
        raise ValueError("attempt must be between 0 and 2")
    resolved = resolve_principal(caller)
    now = datetime.now(UTC)
    with get_connection() as conn:
        active = knowledge_store.list_by_status_with_embeddings(conn, KnowledgeStatus.ACTIVE)
        # 时效校验：status=active 不代表"现在就该被搜到"——还没到生效时间、
        # 或者已经过了失效时间的知识，都不该出现在结果里，哪怕字面/语义都
        # 命中。原方案 §7 检索流程里明确列了这一步。
        valid = [
            (obj, emb)
            for obj, emb in active
            if knowledge_service.is_currently_valid(obj, now=now)
        ]
        candidates = (
            [(obj, emb) for obj, emb in valid if obj.type == knowledge_type]
            if knowledge_type is not None
            else valid
        )
        indexed = None
        if pipeline.enabled():
            try:
                indexed = pipeline.search_chunks(
                    query=query,
                    index_objects=[obj for obj, _emb in valid],
                    authorized_objects=[obj for obj, _emb in candidates],
                    limit=limit,
                    attempt=attempt,
                )
            except (ApiError, TransportError, OSError, ValueError, RuntimeError):
                indexed = None
        if indexed is not None:
            by_id = {obj.knowledge_id: obj for obj, _emb in candidates}
            retrieval_mode: Literal["hybrid", "bm25_only"] = (
                "hybrid" if indexed.used_vector else "bm25_only"
            )
            results = [
                SearchResult(
                    knowledge_id=ranked.hit.parent_id,
                    title=by_id[ranked.hit.parent_id].title,
                    snippet=ranked.hit.text,
                    score=(
                        ranked.relevance_score
                        if indexed.reranker_used
                        else ranked.hit.retrieval_score
                    ),
                    source=by_id[ranked.hit.parent_id].source,
                    version=ranked.hit.parent_version,
                    authority_level=by_id[ranked.hit.parent_id].authority_level,
                    status=by_id[ranked.hit.parent_id].status,
                    chunk_id=ranked.hit.chunk_id,
                    heading_path=list(ranked.hit.heading_path),
                    retrieval_score=ranked.hit.retrieval_score,
                    relevance_score=ranked.relevance_score if indexed.reranker_used else None,
                )
                for ranked in indexed.hits
            ]
            backend: Literal["elasticsearch", "sqlite_fallback"] = "elasticsearch"
            grade = indexed.grade
        else:
            rank_result = hybrid.rank(candidates, query, limit)
            retrieval_mode = "hybrid" if rank_result.used_vector_search else "bm25_only"
            results = [
                SearchResult(
                    knowledge_id=obj.knowledge_id,
                    title=obj.title,
                    snippet=obj.body[:200],
                    score=score,
                    source=obj.source,
                    version=obj.version,
                    authority_level=obj.authority_level,
                    status=obj.status,
                )
                for obj, score in rank_result.results
            ]
            backend = "sqlite_fallback"
            grade = "unavailable"
        # ES 是派生索引。即使审批/废弃恰好与检索并发，也以 SQLite 此刻的
        # 状态和时效为准，不能把旧索引中的正文交给调用方。
        currently_valid = {
            obj.knowledge_id: obj
            for obj, _emb in knowledge_store.list_by_status_with_embeddings(
                conn, KnowledgeStatus.ACTIVE
            )
            if knowledge_service.is_currently_valid(obj, now=datetime.now(UTC))
        }
        results = [
            item
            for item in results
            if item.knowledge_id in currently_valid
            and item.version == currently_valid[item.knowledge_id].version
        ]
        if indexed is not None and grade == "pass" and not results:
            grade = "retry" if attempt < 2 else "insufficient"
        principal_type, principal_id, session_id = _principal_type_and_id(resolved)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now,
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="knowledge.search",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps(
                    {
                        "query": redact(query),
                        "knowledge_type": knowledge_type.value if knowledge_type else None,
                        "attempt": attempt,
                    }
                ),
                result_summary=(
                    f"{len(results)} results, backend={backend}, "
                    f"retrieval_mode={retrieval_mode}, grade={grade}"
                ),
            ),
        )
    return SearchResponse(
        query=query,
        results=results,
        retrieval_mode=retrieval_mode,
        retrieval_backend=backend,
        relevance_grade=grade,
        attempt=attempt,
        remaining_rewrites=2 - attempt if grade == "retry" else 0,
    )
