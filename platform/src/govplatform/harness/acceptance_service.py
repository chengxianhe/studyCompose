from __future__ import annotations

import json

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.contract import service as contract_service
from govplatform.contract.models import VerificationType
from govplatform.db.connection import get_connection
from govplatform.harness import store as harness_store
from govplatform.harness._shared import (
    MAX_REPAIR_ROUNDS,
    HarnessStateError,
    now,
    principal_type_and_id,
)
from govplatform.harness.models import AcceptanceResult, HarnessRun, HarnessStatus, RepairRound
from govplatform.identity.models import Human, Principal, resolve_principal


def record_acceptance(
    *, run_id: str, caller: Principal, results: list[AcceptanceResult]
) -> HarnessRun:
    """记录一轮独立验收结果，内部判定整体通不通过：

    - 提交的 `results` 里，`ac_id` 不能重复、不能引用契约里不存在的 AC
      ——重复/未知的 ac_id 说明证据本身就有问题（同一条 AC 一次提交里
      既报通过又报失败，是自相矛盾的证据），直接拒绝整批，不猜哪条数的。
    - 契约里每条 AC，要么在这批结果里标 passed，要么有一个当前未过期的
      豁免覆盖（`contract_service.is_ac_waived()`），两者都没有就是"未
      解决"。
    - `verification_type == manual_evidence` 的 AC 是例外：这类 AC 设计
      上就是"自动跑不出结论，需要人亲自看"，所以哪怕这批结果里标了
      `passed=True`，只有当这次调用的 caller 本身就是 Human 时才算数；
      Agent 提交的 `passed=True` 对这类 AC 一律当作没有解决处理。
    - 全部解决 -> PASSED。
    - 未解决的里，只要有一条不是 manual_evidence（真的需要重新开发）——
      还没到 3 轮修复上限 -> REPAIRING，轮次 +1；已经是第 3 轮 -> ESCALATED。
    - 未解决的**全部**是 manual_evidence（代码没问题，就差人确认）——
      WAITING_FOR_HUMAN，不消耗修复轮次，等人亲自调用本函数或者批豁免。
    """
    resolved = resolve_principal(caller)
    is_human_caller = isinstance(resolved, Human)
    moment = now()
    principal_type, principal_id, session_id = principal_type_and_id(resolved)
    with get_connection() as conn:
        existing = harness_store.get(conn, run_id)
        if existing is None:
            raise HarnessStateError(f"unknown run_id {run_id!r}")
        if existing.status not in (HarnessStatus.ACCEPTING, HarnessStatus.WAITING_FOR_HUMAN):
            raise HarnessStateError(
                f"run_id {run_id!r} is {existing.status.value}，必须先通过入门禁才能记录验收结果"
            )
        contract = contract_service.get_without_audit(existing.contract_id)
        assert contract is not None  # frozen 契约不会被删

        ac_by_id = {ac.ac_id: ac for ac in contract.acceptance_criteria}
        all_ac_ids = set(ac_by_id)

        result_ac_ids = [r.ac_id for r in results]
        unknown_ids = sorted(set(result_ac_ids) - all_ac_ids)
        if unknown_ids:
            raise HarnessStateError(f"results 引用了契约里不存在的 AC：{unknown_ids}")
        duplicate_ids = sorted({ac_id for ac_id in result_ac_ids if result_ac_ids.count(ac_id) > 1})
        if duplicate_ids:
            raise HarnessStateError(
                f"results 里同一条 AC 出现了不止一次，证据自相矛盾：{duplicate_ids}"
            )

        def _counts_as_passed(result: AcceptanceResult) -> bool:
            if not result.passed:
                return False
            ac = ac_by_id[result.ac_id]
            if ac.verification_type == VerificationType.MANUAL_EVIDENCE:
                return is_human_caller
            return True

        passed_ac_ids = {r.ac_id for r in results if _counts_as_passed(r)}
        waived_ac_ids = {
            ac_id
            for ac_id in all_ac_ids - passed_ac_ids
            if contract_service.is_ac_waived(existing.contract_id, ac_id, now=moment)
        }
        unresolved = sorted(all_ac_ids - passed_ac_ids - waived_ac_ids)
        needs_human_ids = {
            ac_id
            for ac_id in unresolved
            if ac_by_id[ac_id].verification_type == VerificationType.MANUAL_EVIDENCE
        }
        needs_repair_ids = set(unresolved) - needs_human_ids

        new_repair_round = existing.repair_round
        new_repair_rounds = existing.repair_rounds
        escalation_reason: str | None = None

        if not unresolved:
            new_status = HarnessStatus.PASSED
        elif needs_repair_ids:
            if existing.repair_round < MAX_REPAIR_ROUNDS:
                new_status = HarnessStatus.REPAIRING
                new_repair_round = existing.repair_round + 1
                new_repair_rounds = [
                    *existing.repair_rounds,
                    RepairRound(
                        round_number=new_repair_round,
                        failure_summary=f"未通过/未豁免的 AC：{unresolved}",
                        started_at=moment,
                    ),
                ]
            else:
                new_status = HarnessStatus.ESCALATED
                escalation_reason = f"三轮修复后仍未通过/未豁免的 AC：{unresolved}"
        else:
            # unresolved 非空，但里面全是 manual_evidence——代码没问题，
            # 不该消耗修复轮次，停下来等人。
            new_status = HarnessStatus.WAITING_FOR_HUMAN

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
                action="harness.record_acceptance",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"run_id": run_id, "ac_count": len(results)}),
                result_summary=f"status={updated.status.value}",
            ),
        )
    return updated
