from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from govplatform import embedding as embedding_module
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
from govplatform.knowledge.store import StoredEmbedding


class ProposeResponse(BaseModel):
    knowledge_id: str
    status: KnowledgeStatus
    version: int


class ApprovalError(Exception):
    """approve() 因为状态不对（而不是身份不对）被拒绝时抛出。"""


class SensitiveContentError(Exception):
    """propose() 因为正文疑似包含敏感信息被拒绝时抛出。"""


class InvalidTimeRangeError(Exception):
    """propose() 因为 expire_at 不晚于 effective_at 被拒绝时抛出。"""


def _now() -> datetime:
    return datetime.now(UTC)


def _ensure_utc(value: datetime | None) -> datetime | None:
    """把调用方传进来的时间统一成带时区的 UTC。

    调用方（MCP 客户端、HTTP 请求）传的时间可能没带时区信息，如果原样存
    进去，之后跟 `datetime.now(UTC)` 比较时 Python 会直接抛异常（不能比较
    带时区和不带时区的时间）——这里在写入前统一处理掉，而不是等比较那一刻
    才崩。不带时区的一律当成 UTC，不去猜调用方本地时区是什么。
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
    effective_at: datetime | None = None,
    expire_at: datetime | None = None,
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
    effective_at = _ensure_utc(effective_at)
    expire_at = _ensure_utc(expire_at)
    if effective_at is not None and expire_at is not None and expire_at <= effective_at:
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
                    request_json=json.dumps({"reason_category": "invalid_time_range"}),
                    result_summary="rejected: expire_at <= effective_at",
                ),
            )
        raise InvalidTimeRangeError(
            f"expire_at（{expire_at.isoformat()}）必须晚于 "
            f"effective_at（{effective_at.isoformat()}），否则这条知识永远不会被搜到"
        )
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
        effective_at=effective_at,
        expire_at=expire_at,
        content_hash=hashlib.sha256(body.encode("utf-8")).hexdigest(),
        created_at=now,
        updated_at=now,
    )
    # 算向量是"锦上添花"，不是核心写入路径——首次下载模型失败、模型加载
    # 出错等情况，不该连"提交待审核知识"这个最基本的操作都搭进去。失败就
    # 存 embedding=None，检索那边（search/hybrid.py）本来就会跳过没有
    # 向量的候选，自动退化成只用 BM25，不会报错。
    embedding_failed = False
    try:
        vector = embedding_module.embed(f"{title}\n{body}")
        embedding = StoredEmbedding(vector, embedding_module.MODEL_NAME)
    except Exception:
        embedding = StoredEmbedding(None, None)
        embedding_failed = True
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    with get_connection() as conn:
        knowledge_store.insert(conn, obj, embedding)
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
                result_summary=(
                    f"created status={obj.status.value}"
                    + (" (embedding failed, BM25-only for now)" if embedding_failed else "")
                ),
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


def get(knowledge_id: str) -> KnowledgeObject | None:
    with get_connection() as conn:
        return knowledge_store.get(conn, knowledge_id)


def is_currently_valid(obj: KnowledgeObject, *, now: datetime | None = None) -> bool:
    """`obj` 现在是不是"真的生效"：状态是 active，且当前时间落在
    effective_at/expire_at 区间内。`search/service.py` 和
    `contract/service.py`（冻结时校验 knowledge_refs）都要用这条判断，
    抽出来避免两边各写一份、以后改一处漏一处。
    """
    moment = now if now is not None else _now()
    return (
        obj.status == KnowledgeStatus.ACTIVE
        and (obj.effective_at is None or obj.effective_at <= moment)
        and (obj.expire_at is None or obj.expire_at > moment)
    )
