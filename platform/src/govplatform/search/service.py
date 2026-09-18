from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import BaseModel

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.db.connection import get_connection
from govplatform.identity.models import Human, Principal, resolve_principal
from govplatform.knowledge import store as knowledge_store
from govplatform.knowledge.models import AuthorityLevel, KnowledgeStatus, KnowledgeType
from govplatform.knowledge.sensitive import redact
from govplatform.search.index import BM25Corpus


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
        candidates = knowledge_store.list_by_status(conn, KnowledgeStatus.ACTIVE)
        if knowledge_type is not None:
            candidates = [obj for obj in candidates if obj.type == knowledge_type]
        corpus = BM25Corpus(candidates)
        ranked = corpus.query(query, limit)
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
            for obj, score in ranked
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
                result_summary=f"{len(results)} results",
            ),
        )
    return SearchResponse(query=query, results=results)
