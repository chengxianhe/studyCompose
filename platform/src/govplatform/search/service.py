from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.db.connection import get_connection
from govplatform.identity.models import Human, Principal, resolve_principal
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge import store as knowledge_store
from govplatform.knowledge.models import AuthorityLevel, KnowledgeStatus, KnowledgeType
from govplatform.knowledge.sensitive import redact
from govplatform.search import hybrid


class SearchResult(BaseModel):
    knowledge_id: str
    title: str
    snippet: str
    score: float
    source: str
    version: int
    authority_level: AuthorityLevel
    status: KnowledgeStatus


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    # "hybrid" = BM25+向量都参与了这次排序；"bm25_only" = 向量那一路没有
    # 真正贡献结果（模型失败，或者候选里没有能比的向量）——调用方能看出
    # 这次结果是不是缺了语义检索这条证据链，不用去猜。
    retrieval_mode: Literal["hybrid", "bm25_only"]


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
) -> SearchResponse:
    resolved = resolve_principal(caller)
    now = datetime.now(UTC)
    with get_connection() as conn:
        candidates = knowledge_store.list_by_status_with_embeddings(conn, KnowledgeStatus.ACTIVE)
        if knowledge_type is not None:
            candidates = [(obj, emb) for obj, emb in candidates if obj.type == knowledge_type]
        # 时效校验：status=active 不代表"现在就该被搜到"——还没到生效时间、
        # 或者已经过了失效时间的知识，都不该出现在结果里，哪怕字面/语义都
        # 命中。原方案 §7 检索流程里明确列了这一步。
        candidates = [
            (obj, emb)
            for obj, emb in candidates
            if knowledge_service.is_currently_valid(obj, now=now)
        ]
        rank_result = hybrid.rank(candidates, query, limit)
        retrieval_mode: Literal["hybrid", "bm25_only"] = (
            "hybrid" if rank_result.used_vector_search else "bm25_only"
        )
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
                    }
                ),
                result_summary=f"{len(results)} results, retrieval_mode={retrieval_mode}",
            ),
        )
    return SearchResponse(query=query, results=results, retrieval_mode=retrieval_mode)
