from __future__ import annotations

import json

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.contract import store as contract_store
from govplatform.contract._shared import (
    ContractConflictError,
    ContractStateError,
    SensitiveContentError,
    get_without_audit,
    now,
    principal_type_and_id,
    sensitive_reason_in_contract,
)
from govplatform.contract.models import (
    AcceptanceCriterion,
    Contract,
    ContractStatus,
    VerificationCase,
)
from govplatform.db.connection import get_connection
from govplatform.identity.models import Principal, resolve_principal


def update(
    *,
    contract_id: str,
    caller: Principal,
    expected_version: int,
    title: str | None = None,
    goal: str | None = None,
    scope: str | None = None,
    out_of_scope: str | None = None,
    acceptance_criteria: list[AcceptanceCriterion] | None = None,
    test_cases: list[VerificationCase] | None = None,
    knowledge_refs: list[str] | None = None,
    risks: list[str] | None = None,
    open_questions: list[str] | None = None,
) -> Contract:
    resolved = resolve_principal(caller)
    principal_type, principal_id, session_id = principal_type_and_id(resolved)

    existing = get_without_audit(contract_id)
    if existing is None:
        raise ContractStateError(f"unknown contract_id {contract_id!r}")
    if existing.status != ContractStatus.DRAFT:
        raise ContractStateError(
            f"contract_id {contract_id!r} is {existing.status.value}, only draft contracts "
            "can be updated"
        )
    if existing.version != expected_version:
        raise ContractConflictError(
            f"contract_id {contract_id!r} 已经被改过了（当前版本 {existing.version}，"
            f"你传的 expected_version 是 {expected_version}）——重新 get() 一次最新内容，"
            "基于最新版本再改，不要凭旧数据覆盖别人的修改"
        )
    # 上面这个检查只给非并发场景一个快速、清楚的报错，不是真正的保护——
    # 它基于几行前读到的 existing，读和下面真正写入之间仍有窗口。真正的
    # 原子保护在 contract_store.update() 的 `WHERE ... AND version = ?`，
    # 那条 SQL 语句本身就是"检查+写入"合一的，才是乐观锁真正生效的地方。

    merged_ac = (
        acceptance_criteria if acceptance_criteria is not None else existing.acceptance_criteria
    )
    merged_test_cases = test_cases if test_cases is not None else existing.test_cases
    merged_risks = risks if risks is not None else existing.risks
    merged_open_questions = (
        open_questions if open_questions is not None else existing.open_questions
    )
    reason = sensitive_reason_in_contract(
        title=title if title is not None else existing.title,
        goal=goal if goal is not None else existing.goal,
        scope=scope if scope is not None else existing.scope,
        out_of_scope=out_of_scope if out_of_scope is not None else existing.out_of_scope,
        acceptance_criteria=merged_ac,
        test_cases=merged_test_cases,
        risks=merged_risks,
        open_questions=merged_open_questions,
    )
    if reason is not None:
        with get_connection() as conn:
            insert_audit_event(
                conn,
                AuditEvent(
                    occurred_at=now(),
                    principal_type=principal_type,
                    principal_id=principal_id,
                    session_id=session_id,
                    action="contract.update.rejected",
                    knowledge_id=None,
                    knowledge_version=None,
                    request_json=json.dumps(
                        {"contract_id": contract_id, "reason_category": reason}
                    ),
                    result_summary="rejected: sensitive content detected",
                ),
            )
        raise SensitiveContentError(f"疑似包含敏感信息（{reason}），拒绝更新")

    updated = existing.model_copy(
        update={
            "title": title if title is not None else existing.title,
            "goal": goal if goal is not None else existing.goal,
            "scope": scope if scope is not None else existing.scope,
            "out_of_scope": out_of_scope if out_of_scope is not None else existing.out_of_scope,
            "acceptance_criteria": merged_ac,
            "test_cases": merged_test_cases,
            "knowledge_refs": (
                knowledge_refs if knowledge_refs is not None else existing.knowledge_refs
            ),
            "risks": merged_risks,
            "open_questions": merged_open_questions,
            "version": existing.version + 1,
            "updated_at": now(),
        }
    )
    # 真正的乐观锁在 contract_store.update() 内部的 `WHERE ... AND
    # version = ?` 生效。这里不能在同一个 get_connection() 块里写入失败
    # 时直接 raise——块内任何异常都会把这个块自己的写入也回滚掉（无所谓，
    # 写入本来就没生效），但如果紧接着还想在同一个块里写审计事件再 raise，
    # 审计也会被一起回滚。更麻烦的是：这个块的连接此刻可能还持有一个未
    # 提交的写事务（哪怕 UPDATE 影响了 0 行，sqlite3 也会隐式开一个事务），
    # 这时候再嵌套开一个新连接去写审计，会因为文件锁拿不到而报错。所以让
    # 这个块正常退出（提交/不提交都行，反正没有实际改动），连接释放后再
    # 单独开一个新连接写审计、提交、然后在块外 raise——彻底避免锁冲突，
    # 也避免审计被回滚。
    with get_connection() as conn:
        write_succeeded = contract_store.update(conn, updated, expected_version=expected_version)
        if write_succeeded:
            insert_audit_event(
                conn,
                AuditEvent(
                    occurred_at=updated.updated_at,
                    principal_type=principal_type,
                    principal_id=principal_id,
                    session_id=session_id,
                    action="contract.update",
                    knowledge_id=None,
                    knowledge_version=None,
                    request_json=json.dumps(
                        {"contract_id": contract_id, "new_version": updated.version}
                    ),
                    result_summary="updated",
                ),
            )

    if not write_succeeded:
        with get_connection() as audit_conn:
            insert_audit_event(
                audit_conn,
                AuditEvent(
                    occurred_at=now(),
                    principal_type=principal_type,
                    principal_id=principal_id,
                    session_id=session_id,
                    action="contract.update.rejected",
                    knowledge_id=None,
                    knowledge_version=None,
                    request_json=json.dumps(
                        {"contract_id": contract_id, "expected_version": expected_version}
                    ),
                    result_summary="rejected: version conflict at write time",
                ),
            )
        raise ContractConflictError(
            f"contract_id {contract_id!r} 在写入前被并发改过了——重新 get() 一次"
            "最新内容，基于最新版本再改"
        )
    return updated
