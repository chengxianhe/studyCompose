from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.contract import store as contract_store
from govplatform.contract.models import (
    AcceptanceCriterion,
    Contract,
    ContractStatus,
    KnowledgeSnapshot,
    VerificationCase,
)
from govplatform.db.connection import get_connection
from govplatform.identity.models import (
    Human,
    Principal,
    PrincipalNotAllowedError,
    resolve_principal,
)
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.sensitive import find_sensitive_reason


class ContractStateError(Exception):
    """update() 操作已冻结的契约、或 freeze() 操作非草稿状态时抛出。"""


class ContractValidationError(Exception):
    """freeze() 时结构校验不通过（AC/TC 引用不完整）时抛出。"""


class SensitiveContentError(Exception):
    """create()/update() 因为正文疑似包含敏感信息被拒绝时抛出。"""


def _now() -> datetime:
    return datetime.now(UTC)


def _principal_type_and_id(principal: Principal) -> tuple[str, str, str | None]:
    if isinstance(principal, Human):
        return "human", principal.id, None
    return "agent", principal.kind, principal.session_id


def _sensitive_reason_in_contract(
    *,
    title: str,
    goal: str,
    scope: str,
    out_of_scope: str | None,
    acceptance_criteria: list[AcceptanceCriterion],
    risks: list[str],
    open_questions: list[str],
) -> str | None:
    ac_texts = [
        text
        for ac in acceptance_criteria
        for text in (ac.precondition, ac.action, ac.input, ac.expected_result)
    ]
    return find_sensitive_reason(
        title, goal, scope, out_of_scope or "", *ac_texts, *risks, *open_questions
    )


def create(
    *,
    title: str,
    goal: str,
    scope: str,
    caller: Principal,
    out_of_scope: str | None = None,
    acceptance_criteria: list[AcceptanceCriterion] | None = None,
    test_cases: list[VerificationCase] | None = None,
    knowledge_refs: list[str] | None = None,
    risks: list[str] | None = None,
    open_questions: list[str] | None = None,
) -> Contract:
    resolved = resolve_principal(caller)
    acceptance_criteria = acceptance_criteria or []
    risks = risks or []
    open_questions = open_questions or []
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)

    reason = _sensitive_reason_in_contract(
        title=title,
        goal=goal,
        scope=scope,
        out_of_scope=out_of_scope,
        acceptance_criteria=acceptance_criteria,
        risks=risks,
        open_questions=open_questions,
    )
    if reason is not None:
        with get_connection() as conn:
            insert_audit_event(
                conn,
                AuditEvent(
                    occurred_at=_now(),
                    principal_type=principal_type,
                    principal_id=principal_id,
                    session_id=session_id,
                    action="contract.create.rejected",
                    knowledge_id=None,
                    knowledge_version=None,
                    request_json=json.dumps({"reason_category": reason}),
                    result_summary="rejected: sensitive content detected",
                ),
            )
        raise SensitiveContentError(f"疑似包含敏感信息（{reason}），拒绝创建")

    now = _now()
    contract = Contract(
        contract_id=uuid.uuid4().hex,
        title=title,
        goal=goal,
        scope=scope,
        out_of_scope=out_of_scope,
        author=resolved,
        status=ContractStatus.DRAFT,
        version=1,
        acceptance_criteria=acceptance_criteria,
        test_cases=test_cases or [],
        knowledge_refs=knowledge_refs or [],
        risks=risks,
        open_questions=open_questions,
        created_at=now,
        updated_at=now,
    )
    with get_connection() as conn:
        contract_store.insert(conn, contract)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now,
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="contract.create",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"contract_id": contract.contract_id, "title": title}),
                result_summary=f"created status={contract.status.value}",
            ),
        )
    return contract


def update(
    *,
    contract_id: str,
    caller: Principal,
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
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)

    existing = get_without_audit(contract_id)
    if existing is None:
        raise ContractStateError(f"unknown contract_id {contract_id!r}")
    if existing.status != ContractStatus.DRAFT:
        raise ContractStateError(
            f"contract_id {contract_id!r} is {existing.status.value}, only draft contracts "
            "can be updated"
        )

    merged_ac = (
        acceptance_criteria if acceptance_criteria is not None else existing.acceptance_criteria
    )
    merged_risks = risks if risks is not None else existing.risks
    merged_open_questions = (
        open_questions if open_questions is not None else existing.open_questions
    )
    reason = _sensitive_reason_in_contract(
        title=title if title is not None else existing.title,
        goal=goal if goal is not None else existing.goal,
        scope=scope if scope is not None else existing.scope,
        out_of_scope=out_of_scope if out_of_scope is not None else existing.out_of_scope,
        acceptance_criteria=merged_ac,
        risks=merged_risks,
        open_questions=merged_open_questions,
    )
    if reason is not None:
        with get_connection() as conn:
            insert_audit_event(
                conn,
                AuditEvent(
                    occurred_at=_now(),
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
            "test_cases": test_cases if test_cases is not None else existing.test_cases,
            "knowledge_refs": (
                knowledge_refs if knowledge_refs is not None else existing.knowledge_refs
            ),
            "risks": merged_risks,
            "open_questions": merged_open_questions,
            "updated_at": _now(),
        }
    )
    with get_connection() as conn:
        contract_store.update(conn, updated)
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
                request_json=json.dumps({"contract_id": contract_id}),
                result_summary="updated",
            ),
        )
    return updated


def _validation_errors(contract: Contract) -> tuple[list[str], list[KnowledgeSnapshot]]:
    errors: list[str] = []
    if not contract.acceptance_criteria:
        errors.append("acceptance_criteria 不能为空——契约至少要有一条验收标准")

    ac_ids = [ac.ac_id for ac in contract.acceptance_criteria]
    if len(ac_ids) != len(set(ac_ids)):
        errors.append("ac_id 有重复")

    tc_ids = [tc.tc_id for tc in contract.test_cases]
    if len(tc_ids) != len(set(tc_ids)):
        errors.append("tc_id 有重复")
    tc_id_set = set(tc_ids)

    # 对应原方案 §9.2："每条 AC-* 必须有唯一ID，并具备前置条件、操作、
    # 输入、二值化预期结果和验证证据类型"——这里只查字段填没填（结构），
    # 不判断写得好不好（内容质量留给人审）。
    required_fields = ("precondition", "action", "input", "expected_result")
    for ac in contract.acceptance_criteria:
        empty_fields = [field for field in required_fields if not getattr(ac, field).strip()]
        if empty_fields:
            errors.append(f"{ac.ac_id} 缺少必填字段：{empty_fields}")
        if not ac.test_case_ids:
            errors.append(f"{ac.ac_id} 没有关联任何测试用例（TC-*）")
            continue
        missing = [tc_id for tc_id in ac.test_case_ids if tc_id not in tc_id_set]
        if missing:
            errors.append(f"{ac.ac_id} 引用了不存在的测试用例：{missing}")

    # knowledge_service.get() 自己管理连接，这里不复用 freeze() 已经打开
    # 的那个——SQLite 支持同一个文件的多个只读连接同时存在，简单起见不去
    # 传递/复用底层连接对象。
    snapshots: list[KnowledgeSnapshot] = []
    now = _now()
    for knowledge_id in contract.knowledge_refs:
        knowledge = knowledge_service.get(knowledge_id)
        if knowledge is None:
            errors.append(f"knowledge_refs 引用了不存在的知识：{knowledge_id}")
        elif not knowledge_service.is_currently_valid(knowledge, now=now):
            errors.append(
                f"knowledge_refs 引用的知识不是当前生效状态："
                f"{knowledge_id}（status={knowledge.status.value}）"
            )
        else:
            snapshots.append(
                KnowledgeSnapshot(
                    knowledge_id=knowledge_id,
                    version=knowledge.version,
                    content_hash=knowledge.content_hash,
                )
            )

    return errors, snapshots


def freeze(*, contract_id: str, caller: Principal) -> Contract:
    resolved = resolve_principal(caller)
    if not isinstance(resolved, Human):
        raise PrincipalNotAllowedError("only a human owner can freeze a contract")
    now = _now()
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)

    existing = get_without_audit(contract_id)
    if existing is None:
        raise ContractStateError(f"unknown contract_id {contract_id!r}")
    if existing.status != ContractStatus.DRAFT:
        raise ContractStateError(f"contract_id {contract_id!r} is already {existing.status.value}")

    errors, snapshots = _validation_errors(existing)
    if errors:
        # 拒绝审计要记进去，不能跟下面失败的 raise 共用同一个连接块——
        # get_connection() 的设计是块内任何异常都会回滚整个事务，如果
        # 审计写入和 raise 挤在同一个 with 块里，刚写的审计记录会被这次
        # 回滚一起吞掉。单独开一个连接块，写完提交了再在块外面抛异常，
        # 跟 knowledge/service.py 里敏感内容拒绝那段是同一个模式。
        with get_connection() as conn:
            insert_audit_event(
                conn,
                AuditEvent(
                    occurred_at=now,
                    principal_type=principal_type,
                    principal_id=principal_id,
                    session_id=session_id,
                    action="contract.freeze.rejected",
                    knowledge_id=None,
                    knowledge_version=None,
                    request_json=json.dumps({"contract_id": contract_id}),
                    result_summary=f"rejected: {'; '.join(errors)}",
                ),
            )
        raise ContractValidationError("；".join(errors))

    frozen = existing.model_copy(
        update={
            "status": ContractStatus.FROZEN,
            "knowledge_snapshots": snapshots,
            "frozen_by": resolved.id,
            "frozen_at": now,
            "updated_at": now,
        }
    )
    with get_connection() as conn:
        contract_store.update(conn, frozen)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now,
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="contract.freeze",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"contract_id": contract_id}),
                result_summary="status=frozen",
            ),
        )
    return frozen


def get_without_audit(contract_id: str) -> Contract | None:
    """内部/跨模块用——不记审计，因为调用方（update()/freeze() 自身、
    以后可能有的其他内部逻辑）已经在各自的操作里记了审计，不需要"读一次"
    也单独记一条。对外暴露给 MCP/HTTP 的读操作用下面的 get()，会记审计。
    """
    with get_connection() as conn:
        return contract_store.get(conn, contract_id)


def get(contract_id: str, *, caller: Principal) -> Contract | None:
    resolved = resolve_principal(caller)
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    contract = get_without_audit(contract_id)
    with get_connection() as conn:
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=_now(),
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="contract.get",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"contract_id": contract_id}),
                result_summary="found" if contract is not None else "not found",
            ),
        )
    return contract
