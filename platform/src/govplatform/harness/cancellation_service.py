import json
from datetime import datetime

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.db.connection import get_connection
from govplatform.harness import store
from govplatform.harness._shared import HarnessStateError, now
from govplatform.harness.models import HarnessRun, HarnessStatus
from govplatform.identity.models import (
    Human,
    Principal,
    PrincipalNotAllowedError,
    resolve_principal,
)
from govplatform.knowledge.sensitive import find_sensitive_reason


def cancel(
    *,
    run_id: str,
    caller: Principal,
    reason: str,
    expected_updated_at: datetime | None = None,
) -> HarnessRun:
    owner = resolve_principal(caller)
    if not isinstance(owner, Human):
        raise PrincipalNotAllowedError("只有用户能取消任务运行")
    reason = reason.strip()
    if not reason or len(reason) > 4000 or find_sensitive_reason(reason):
        raise HarnessStateError("请填写 1 至 4000 字、不含敏感信息的取消原因")
    with get_connection() as conn:
        current = store.get(conn, run_id)
        if current is None or current.status in (
            HarnessStatus.DELIVERED,
            HarnessStatus.ESCALATED,
            HarnessStatus.CANCELLED,
        ):
            raise HarnessStateError("运行不存在或已结束，不能取消")
        if expected_updated_at is not None and current.updated_at != expected_updated_at:
            raise HarnessStateError("运行已变化，请刷新后重新确认取消")
        updated = current.model_copy(
            update={"status": HarnessStatus.CANCELLED, "updated_at": now()}
        )
        if not store.update(conn, updated, expected_updated_at=current.updated_at):
            raise HarnessStateError("运行已变化，请重新读取")
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=updated.updated_at,
                principal_type="human",
                principal_id=owner.id,
                session_id=None,
                action="harness.cancel",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"run_id": run_id, "reason": reason}),
                result_summary="cancelled",
            ),
        )
    return updated
