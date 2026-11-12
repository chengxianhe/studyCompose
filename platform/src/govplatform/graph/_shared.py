from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.graph import store
from govplatform.graph.models import GraphError, KnowledgeRef, Relation, ReviewSnapshot
from govplatform.identity.models import Human, Principal
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge import store as knowledge_store
from govplatform.knowledge.sensitive import find_sensitive_reason


def now() -> datetime:
    return datetime.now(UTC)


def text(value: str, name: str, maximum: int = 4000) -> str:
    value = value.strip()
    if not value or len(value) > maximum:
        raise GraphError(f"{name} must contain 1..{maximum} characters")
    if find_sensitive_reason(value):
        raise GraphError("sensitive content rejected")
    return value


def audit(conn: sqlite3.Connection, caller: Principal, action: str, key: str) -> None:
    insert_audit_event(
        conn,
        AuditEvent(
            occurred_at=now(),
            principal_type=caller.principal_type,
            principal_id=caller.id if isinstance(caller, Human) else caller.kind,
            session_id=None if isinstance(caller, Human) else caller.session_id,
            action=action,
            knowledge_id=None,
            knowledge_version=None,
            request_json=json.dumps({"id": key}),
            result_summary="recorded",
        ),
    )


def knowledge_ref(conn: sqlite3.Connection, key: str) -> KnowledgeRef:
    obj = knowledge_store.get(conn, key)
    if obj is None or not knowledge_service.is_currently_valid(obj):
        raise GraphError("knowledge endpoint must be active and currently valid")
    return KnowledgeRef(knowledge_id=key, version=obj.version, content_hash=obj.content_hash)


def snapshot(conn: sqlite3.Connection, obj: Relation) -> ReviewSnapshot:
    sources = []
    for key in sorted({key for key in (obj.evidence_source_id, obj.target_source_id) if key}):
        source = store.get_source(conn, key)
        if source is None:
            raise GraphError("unknown source revision")
        sources.append(source)
    states: list[dict[str, str | int | bool | None]] = []
    for ref in [obj.subject, *([obj.target_knowledge] if obj.target_knowledge else [])]:
        current = knowledge_store.get(conn, ref.knowledge_id)
        states.append(
            {
                "id": ref.knowledge_id,
                "title": current.title if current else "missing",
                "version": current.version if current else None,
                "hash": current.content_hash if current else None,
                "status": current.status.value if current else "missing",
                "valid": bool(current and knowledge_service.is_currently_valid(current)),
                "effective_at": str(current.effective_at) if current else None,
                "expire_at": str(current.expire_at) if current else None,
            }
        )
    return ReviewSnapshot(relation=obj, sources=sources, knowledge_states=states)


def warnings(conn: sqlite3.Connection, obj: Relation) -> list[str]:
    issues = [] if obj.status == "active" else ["relation_" + obj.status]
    for ref in [obj.subject, *([obj.target_knowledge] if obj.target_knowledge else [])]:
        current = knowledge_store.get(conn, ref.knowledge_id)
        if current is None or not knowledge_service.is_currently_valid(current):
            issues.append("endpoint_not_current:" + ref.knowledge_id)
        if current is None or (current.version, current.content_hash) != (
            ref.version,
            ref.content_hash,
        ):
            issues.append("endpoint_changed:" + ref.knowledge_id)
    return issues
