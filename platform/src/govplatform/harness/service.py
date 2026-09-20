from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.contract import service as contract_service
from govplatform.contract.models import ContractStatus, VerificationType
from govplatform.db.connection import get_connection
from govplatform.harness import store as harness_store
from govplatform.harness.models import (
    AcceptanceResult,
    GateResult,
    HarnessRun,
    HarnessStatus,
    RepairRound,
)
from govplatform.identity.models import (
    Human,
    Principal,
    PrincipalNotAllowedError,
    resolve_principal,
)

# 原方案 §10.4："同一契约下最多三轮修复"。
_MAX_REPAIR_ROUNDS = 3


class HarnessStateError(Exception):
    """在错误的状态下调用 start()/record_entry_gate()/record_acceptance()/
    deliver() 时抛出——比如对一份非 frozen 的契约 start()，或者入门禁还
    没过就想记录验收结果。
    """


def _now() -> datetime:
    return datetime.now(UTC)


def _principal_type_and_id(principal: Principal) -> tuple[str, str, str | None]:
    if isinstance(principal, Human):
        return "human", principal.id, None
    return "agent", principal.kind, principal.session_id


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
    now = _now()
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    run = HarnessRun(
        run_id=uuid.uuid4().hex,
        contract_id=contract_id,
        status=HarnessStatus.DEVELOPING,
        started_by=principal_id,
        created_at=now,
        updated_at=now,
    )
    with get_connection() as conn:
        harness_store.insert(conn, run)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now,
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
    now = _now()
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    with get_connection() as conn:
        existing = harness_store.get(conn, run_id)
        if existing is None:
            raise HarnessStateError(f"unknown run_id {run_id!r}")
        if existing.status not in (HarnessStatus.DEVELOPING, HarnessStatus.REPAIRING):
            raise HarnessStateError(
                f"run_id {run_id!r} is {existing.status.value}，entry gate 只能在开发/修复中记录"
            )
        gate_result = GateResult(passed=passed, command=command, summary=summary, recorded_at=now)
        new_status = HarnessStatus.ACCEPTING if passed else existing.status
        updated = existing.model_copy(
            update={
                "status": new_status,
                "entry_gate_results": [*existing.entry_gate_results, gate_result],
                "updated_at": now,
            }
        )
        harness_store.update(conn, updated)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now,
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


def record_acceptance(
    *, run_id: str, caller: Principal, results: list[AcceptanceResult]
) -> HarnessRun:
    """记录一轮独立验收结果，内部判定整体通不通过：

    - 契约里每条 AC，要么在这批结果里标 passed，要么有一个当前未过期的
      豁免覆盖（`contract_service.is_ac_waived()`），两者都没有就是"未
      解决"。
    - `verification_type == manual_evidence` 的 AC 是例外：这类 AC 设计
      上就是"自动跑不出结论，需要人亲自看"，所以哪怕这批结果里标了
      `passed=True`，只有当这次调用的 caller 本身就是 Human 时才算数；
      Agent 提交的 `passed=True` 对这类 AC 一律当作没有解决处理（不是
      报错——Agent 正常提交自动化 AC 的结果时，捎带一条 Agent 自己判定
      不了的 manual_evidence 结果是常见情况，不该让整次调用失败）。这样
      manual_evidence 类 AC 只能靠 Human 亲自调用本函数、或者 Human 批
      一个豁免来解决，Agent 没法自己给自己判过——对应之前决策时明确选
      的"遇到 manual_evidence 停下来问人"，之前的实现漏掉了这层校验。
    - 全部解决 -> PASSED。
    - 有未解决的，且还没到 3 轮修复上限 -> REPAIRING，轮次 +1。
    - 有未解决的，且已经是第 3 轮 -> ESCALATED，写归因（未解决的 AC 是
      哪几条），这是终态——要继续只能针对同一份契约重新 start() 一次新
      的运行，不会复用/篡改这次的历史。
    """
    resolved = resolve_principal(caller)
    is_human_caller = isinstance(resolved, Human)
    now = _now()
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    with get_connection() as conn:
        existing = harness_store.get(conn, run_id)
        if existing is None:
            raise HarnessStateError(f"unknown run_id {run_id!r}")
        if existing.status != HarnessStatus.ACCEPTING:
            raise HarnessStateError(
                f"run_id {run_id!r} is {existing.status.value}，必须先通过入门禁才能记录验收结果"
            )
        contract = contract_service.get_without_audit(existing.contract_id)
        assert contract is not None  # frozen 契约不会被删

        ac_by_id = {ac.ac_id: ac for ac in contract.acceptance_criteria}
        all_ac_ids = set(ac_by_id)

        def _counts_as_passed(result: AcceptanceResult) -> bool:
            if not result.passed:
                return False
            ac = ac_by_id.get(result.ac_id)
            if ac is not None and ac.verification_type == VerificationType.MANUAL_EVIDENCE:
                return is_human_caller
            return True

        passed_ac_ids = {r.ac_id for r in results if _counts_as_passed(r)}
        waived_ac_ids = {
            ac_id
            for ac_id in all_ac_ids - passed_ac_ids
            if contract_service.is_ac_waived(existing.contract_id, ac_id, now=now)
        }
        unresolved = sorted(all_ac_ids - passed_ac_ids - waived_ac_ids)

        new_repair_round = existing.repair_round
        new_repair_rounds = existing.repair_rounds
        escalation_reason: str | None = None

        if not unresolved:
            new_status = HarnessStatus.PASSED
        elif existing.repair_round < _MAX_REPAIR_ROUNDS:
            new_status = HarnessStatus.REPAIRING
            new_repair_round = existing.repair_round + 1
            new_repair_rounds = [
                *existing.repair_rounds,
                RepairRound(
                    round_number=new_repair_round,
                    failure_summary=f"未通过/未豁免的 AC：{unresolved}",
                    started_at=now,
                ),
            ]
        else:
            new_status = HarnessStatus.ESCALATED
            escalation_reason = f"三轮修复后仍未通过/未豁免的 AC：{unresolved}"

        # acceptance_results 是跨轮次累积的完整历史，不覆盖——覆盖会丢掉
        # 上一轮具体哪条证据、谁提交的，只剩 repair_rounds 里那句粗略的
        # failure_summary，审计链就不完整了。这一批结果盖上当前轮次号后
        # 追加进去，不动之前轮次留下的记录。
        stamped_results = [
            r.model_copy(update={"round_number": existing.repair_round}) for r in results
        ]
        updated = existing.model_copy(
            update={
                "status": new_status,
                "acceptance_results": [*existing.acceptance_results, *stamped_results],
                "repair_round": new_repair_round,
                "repair_rounds": new_repair_rounds,
                "escalation_reason": escalation_reason,
                "updated_at": now,
            }
        )
        harness_store.update(conn, updated)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now,
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="harness.record_acceptance",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"run_id": run_id, "ac_count": len(results)}),
                result_summary=f"status={updated.status.value}",
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
    now = _now()
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
            update={"status": HarnessStatus.DELIVERED, "delivered_at": now, "updated_at": now}
        )
        harness_store.update(conn, updated)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now,
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
