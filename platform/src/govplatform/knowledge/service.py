from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.db.connection import get_connection
from govplatform.identity.models import (
    Human,
    Principal,
    PrincipalNotAllowedError,
    resolve_principal,
)
from govplatform.knowledge import store as knowledge_store
from govplatform.knowledge.models import (
    AuthorityLevel,
    KnowledgeObject,
    KnowledgeStatus,
    KnowledgeType,
)
from govplatform.knowledge.sensitive import find_sensitive_reason


class ProposeResponse(BaseModel):
    knowledge_id: str
    status: KnowledgeStatus
    version: int


class ApprovalError(Exception):
    """approve() 因为状态不对（而不是身份不对）被拒绝时抛出。"""


class SensitiveContentError(Exception):
    """propose() 因为正文疑似包含敏感信息被拒绝时抛出。"""


def _now() -> datetime:
    return datetime.now(UTC)


def _principal_type_and_id(principal: Principal) -> tuple[str, str, str | None]:
    if isinstance(principal, Human):
        return "human", principal.id, None
    return "agent", principal.kind, principal.session_id


def propose(
    *,
    title: str,
    type: KnowledgeType,
    body: str,
    source: str,
    authority_level: AuthorityLevel,
    caller: Principal,
    tags: list[str] | None = None,
) -> KnowledgeObject:
    resolved = resolve_principal(caller)
    reason = find_sensitive_reason(title, body, source, *(tags or []))
    if reason is not None:
        principal_type, principal_id, session_id = _principal_type_and_id(resolved)
        with get_connection() as conn:
            insert_audit_event(
                conn,
                AuditEvent(
                    occurred_at=_now(),
                    principal_type=principal_type,
                    principal_id=principal_id,
                    session_id=session_id,
                    action="knowledge.propose.rejected",
                    knowledge_id=None,
                    knowledge_version=None,
                    request_json=json.dumps({"reason_category": reason}),
                    result_summary="rejected: sensitive content detected",
                ),
            )
        raise SensitiveContentError(f"疑似包含敏感信息（{reason}），拒绝入库")
    now = _now()
    obj = KnowledgeObject(
        knowledge_id=uuid.uuid4().hex,
        title=title,
        type=type,
        body=body,
        source=source,
        author=resolved,
        owner=None,
        authority_level=authority_level,
        status=KnowledgeStatus.IN_REVIEW,
        version=1,
        tags=tags or [],
        content_hash=hashlib.sha256(body.encode("utf-8")).hexdigest(),
        created_at=now,
        updated_at=now,
    )
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    with get_connection() as conn:
        knowledge_store.insert(conn, obj)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now,
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="knowledge.propose",
                knowledge_id=obj.knowledge_id,
                knowledge_version=obj.version,
                request_json=obj.model_dump_json(
                    include={"title", "type", "source", "authority_level"}
                ),
                result_summary=f"created status={obj.status.value}",
            ),
        )
    return obj


def approve(*, knowledge_id: str, caller: Principal) -> KnowledgeObject:
    resolved = resolve_principal(caller)
    if not isinstance(resolved, Human):
        raise PrincipalNotAllowedError("only a human owner can approve knowledge objects")
    now = _now()
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    with get_connection() as conn:
        existing = knowledge_store.get(conn, knowledge_id)
        if existing is None:
            raise ApprovalError(f"unknown knowledge_id {knowledge_id!r}")
        if existing.status != KnowledgeStatus.IN_REVIEW:
            raise ApprovalError(
                f"knowledge_id {knowledge_id!r} is in status {existing.status.value}, not in_review"
            )
        knowledge_store.update_status(
            conn,
            knowledge_id,
            status=KnowledgeStatus.ACTIVE,
            owner=resolved.id,
            updated_at=now,
        )
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now,
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="knowledge.approve",
                knowledge_id=knowledge_id,
                knowledge_version=existing.version,
                request_json=json.dumps({"knowledge_id": knowledge_id}),
                result_summary="status=active",
            ),
        )
        approved = knowledge_store.get(conn, knowledge_id)
    assert approved is not None
    return approved
