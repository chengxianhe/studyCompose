"""可审计的目录与全文查询；候选内容不因此成为有效知识。"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import BaseModel

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.db.connection import get_connection
from govplatform.identity.models import Human, Principal, resolve_principal
from govplatform.knowledge import store
from govplatform.knowledge.models import KnowledgeObject, KnowledgeStatus


class KnowledgePage(BaseModel):
    items: list[KnowledgeObject]
    total: int
    offset: int
    limit: int


def _audit(caller: Principal, action: str, request: dict[str, object], result: str) -> None:
    with get_connection() as conn:
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=datetime.now(UTC),
                principal_type=caller.principal_type,
                principal_id=caller.id if isinstance(caller, Human) else caller.kind,
                session_id=None if isinstance(caller, Human) else caller.session_id,
                action=action,
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps(request),
                result_summary=result,
            ),
        )


def list_knowledge(
    *,
    caller: Principal,
    status: KnowledgeStatus | None = KnowledgeStatus.IN_REVIEW,
    offset: int = 0,
    limit: int = 20,
) -> KnowledgePage:
    resolved = resolve_principal(caller)
    if offset < 0 or not 1 <= limit <= 100:
        raise ValueError("offset must be >= 0; limit must be between 1 and 100")
    where = " WHERE status = ?" if status is not None else ""
    parameters: tuple[str, ...] = (status.value,) if status is not None else ()
    with get_connection() as conn:
        total = int(
            conn.execute(
                "SELECT COUNT(*) FROM knowledge_objects" + where,
                parameters,
            ).fetchone()[0]
        )
        rows = conn.execute(
            "SELECT knowledge_id FROM knowledge_objects"
            + where
            + " ORDER BY created_at DESC, knowledge_id LIMIT ? OFFSET ?",
            (*parameters, limit, offset),
        ).fetchall()
        items = [obj for row in rows if (obj := store.get(conn, row[0])) is not None]
    _audit(
        resolved,
        "knowledge.list",
        {"status": status, "offset": offset, "limit": limit},
        f"returned={len(items)} total={total}",
    )
    return KnowledgePage(items=items, total=total, offset=offset, limit=limit)


def get_knowledge(*, knowledge_id: str, caller: Principal) -> KnowledgeObject | None:
    resolved = resolve_principal(caller)
    with get_connection() as conn:
        obj = store.get(conn, knowledge_id)
    _audit(
        resolved,
        "knowledge.get",
        {"knowledge_id": knowledge_id},
        f"status={obj.status.value} version={obj.version}" if obj else "not found",
    )
    return obj
