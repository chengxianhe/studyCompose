"""Harness 模块对外唯一入口。

`record_acceptance()` 拆去了 `acceptance_service.py`——是这个文件里最
复杂、增长最快的一块，加上项目 250 行/文件的上限撑不住了，拆分理由跟
`contract/service.py` 那次一样，详见 `harness/_shared.py` 顶部注释。
外部调用方继续用 `from govplatform.harness import service as
harness_service` 然后 `harness_service.start/record_entry_gate/
record_acceptance/deliver/get`，不用改任何 import。
"""

from __future__ import annotations

import json
import uuid

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.contract import service as contract_service
from govplatform.contract.models import ContractStatus
from govplatform.db.connection import get_connection
from govplatform.harness import store as harness_store
from govplatform.harness._shared import HarnessStateError as HarnessStateError
from govplatform.harness._shared import now as _now
from govplatform.harness._shared import principal_type_and_id as _principal_type_and_id
from govplatform.harness.acceptance_service import record_acceptance as record_acceptance
from govplatform.harness.models import GateResult, HarnessRun, HarnessStatus
from govplatform.identity.models import (
    Human,
    Principal,
    PrincipalNotAllowedError,
    resolve_principal,
)

__all__ = [
    "HarnessStateError",
    "deliver",
    "get",
    "record_acceptance",
    "record_entry_gate",
    "start",
]


def start(*, contract_id: str, caller: Principal) -> HarnessRun:
    """开始一次 Harness 运行。Human-only——baseline 文档 §7.1 写得很明确：
    "AI 不能自己...启动一轮 Harness 循环"，这条是需求准入身份门禁的延伸，
    不是只管"提需求"那一步。契约冻结只代表"这份契约的内容被人认可了"，
    不能替代"现在要不要真的跑一次"这个单独的人工点火动作——之前的实现
    把这两件事混成一件事了，是设计意图理解错误，这里改回来。一份契约
    可以有多次运行（比如第一次三轮修复后升级，人补了豁免，人再 start()
    一次新的运行）——每次运行独立记录，不会篡改已经 escalate 的旧运行
    历史，跟原方案 §10.4"不得篡改已失败运行的历史"一致。
    """
    resolved = resolve_principal(caller)
    if not isinstance(resolved, Human):
        raise PrincipalNotAllowedError("only a human owner can start a harness run")
    contract = contract_service.get_without_audit(contract_id)
    if contract is None:
        raise HarnessStateError(f"unknown contract_id {contract_id!r}")
    if contract.status != ContractStatus.FROZEN:
        raise HarnessStateError(
            f"contract_id {contract_id!r} is {contract.status.value}, only frozen "
            "contracts can start a harness run"
        )
    moment = _now()
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    run = HarnessRun(
        run_id=uuid.uuid4().hex,
        contract_id=contract_id,
        status=HarnessStatus.DEVELOPING,
        started_by=principal_id,
        created_at=moment,
        updated_at=moment,
    )
    with get_connection() as conn:
        harness_store.insert(conn, run)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=moment,
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="harness.start",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"contract_id": contract_id, "run_id": run.run_id}),
                result_summary=f"status={run.status.value}",
            ),
        )
    return run


def record_entry_gate(
    *, run_id: str, caller: Principal, passed: bool, command: str, summary: str
) -> HarnessRun:
    """记录入门禁（构建/静态检查/测试）结果。没过，状态维持在开发/修复中
    （不消耗修复轮次，不进入验收）；过了才进入 ACCEPTING。
    """
    resolved = resolve_principal(caller)
    moment = _now()
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    with get_connection() as conn:
        existing = harness_store.get(conn, run_id)
        if existing is None:
            raise HarnessStateError(f"unknown run_id {run_id!r}")
        if existing.status not in (HarnessStatus.DEVELOPING, HarnessStatus.REPAIRING):
            raise HarnessStateError(
                f"run_id {run_id!r} is {existing.status.value}，entry gate 只能在开发/修复中记录"
            )
        gate_result = GateResult(
            passed=passed, command=command, summary=summary, recorded_at=moment
        )
        new_status = HarnessStatus.ACCEPTING if passed else existing.status
        updated = existing.model_copy(
            update={
                "status": new_status,
                "entry_gate_results": [*existing.entry_gate_results, gate_result],
                "updated_at": moment,
            }
        )
        harness_store.update(conn, updated)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=moment,
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="harness.record_entry_gate",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"run_id": run_id, "command": command}),
                result_summary=f"passed={passed} status={updated.status.value}",
            ),
        )
    return updated


def deliver(*, run_id: str, caller: Principal) -> HarnessRun:
    """标记这次运行为已交付——只有 Human 能做，只有 PASSED 状态能做。
    Harness 自己能自动跑到 PASSED（所有 AC 通过或者被有效豁免覆盖），
    但不能自己点"交付"，这是"最终交付你来审"这条原则的落地点。
    """
    resolved = resolve_principal(caller)
    if not isinstance(resolved, Human):
        raise PrincipalNotAllowedError("only a human owner can mark a harness run as delivered")
    moment = _now()
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    with get_connection() as conn:
        existing = harness_store.get(conn, run_id)
        if existing is None:
            raise HarnessStateError(f"unknown run_id {run_id!r}")
        if existing.status != HarnessStatus.PASSED:
            raise HarnessStateError(
                f"run_id {run_id!r} is {existing.status.value}, only passed runs can be delivered"
            )
        updated = existing.model_copy(
            update={
                "status": HarnessStatus.DELIVERED,
                "delivered_at": moment,
                "updated_at": moment,
            }
        )
        harness_store.update(conn, updated)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=moment,
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="harness.deliver",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"run_id": run_id}),
                result_summary="status=delivered",
            ),
        )
    return updated


def get(run_id: str, *, caller: Principal) -> HarnessRun | None:
    resolved = resolve_principal(caller)
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    with get_connection() as conn:
        run = harness_store.get(conn, run_id)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=_now(),
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="harness.get",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"run_id": run_id}),
                result_summary="found" if run is not None else "not found",
            ),
        )
    return run
