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
    Waiver,
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


class ContractConflictError(Exception):
    """update() 时 expected_version 跟数据库里当前的版本对不上时抛出。

    契约草稿期可能有多个 Agent（或者你自己）在改，update() 是整份覆盖式
    的——不做这个检查的话，后写的会悄悄覆盖先写的，没有任何提示。调用方
    必须先 get() 拿到当前版本号，带着它来 update()，对不上就说明中间被
    别人改过了，拒绝这次写入，让调用方重新读一遍最新内容再决定怎么改，
    而不是盲目覆盖。
    """


class SensitiveContentError(Exception):
    """create()/update() 因为正文疑似包含敏感信息被拒绝时抛出。"""


class WaiverNotAllowedError(Exception):
    """request_waiver() 针对 touches_production_or_irreversible 的 AC 时抛出。

    对应 baseline 文档 §7.3 从 Anthropic 自己公开实践调研来的限制：
    涉及生产数据/不可逆操作的验收标准，没有豁免这条路，必须真通过。
    """


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
    test_cases: list[VerificationCase],
    risks: list[str],
    open_questions: list[str],
) -> str | None:
    ac_texts = [
        text
        for ac in acceptance_criteria
        for text in (ac.precondition, ac.action, ac.input, ac.expected_result)
    ]
    tc_texts = [tc.description for tc in test_cases]
    return find_sensitive_reason(
        title, goal, scope, out_of_scope or "", *ac_texts, *tc_texts, *risks, *open_questions
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
        test_cases=test_cases or [],
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
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)

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
    # 上面这个检查只是给正常（非并发）情况一个快速、清楚的错误提示，不是
    # 真正的保护——它基于几行代码之前读到的 `existing`，读和下面真正写入
    # 之间仍有窗口。真正的原子保护在 contract_store.update() 的
    # `WHERE ... AND version = ?`，那条 SQL 语句本身就是"检查+写入"合一
    # 的，才是这个乐观锁真正生效的地方。

    merged_ac = (
        acceptance_criteria if acceptance_criteria is not None else existing.acceptance_criteria
    )
    merged_test_cases = test_cases if test_cases is not None else existing.test_cases
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
        test_cases=merged_test_cases,
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
            "test_cases": merged_test_cases,
            "knowledge_refs": (
                knowledge_refs if knowledge_refs is not None else existing.knowledge_refs
            ),
            "risks": merged_risks,
            "open_questions": merged_open_questions,
            "version": existing.version + 1,
            "updated_at": _now(),
        }
    )
    # 真正的乐观锁在 contract_store.update() 内部的 `WHERE ... AND
    # version = ?` 生效。这里不能在同一个 get_connection() 块里，写入
    # 失败时直接 raise——块内任何异常都会把这个块自己的写入也回滚掉，这
    # 无所谓（写入本来就没生效），但如果紧接着还想在同一个块里写审计
    # 事件再 raise，审计也会被一起回滚。更麻烦的是：这个块的连接此刻可能
    # 还持有一个未提交的写事务（哪怕 UPDATE 影响了 0 行，sqlite3 也会
    # 隐式开一个事务），这时候再嵌套开一个新连接去写审计，会因为文件锁
    # 拿不到而报错。所以这里让这个块正常退出（提交或者不提交都行，反正
    # 没有实际改动），退出后连接释放，再在块外单独开一个新连接写审计、
    # 提交、然后 raise——彻底避免锁冲突，也避免审计被回滚。
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
                    occurred_at=_now(),
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

    # 对应 baseline 文档 §7.3 从"变更三板斧"调研来的限制：涉及生产数据/
    # 不可逆操作的 AC，契约必须写清楚回滚方案（risks 不能为空）——只查
    # "写没写"，不判断回滚方案写得好不好。
    if any(ac.touches_production_or_irreversible for ac in contract.acceptance_criteria) and (
        not contract.risks
    ):
        errors.append(
            "有验收标准标了 touches_production_or_irreversible，"
            "risks 字段必须写清楚回滚方案，不能为空"
        )

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


def request_waiver(
    *,
    contract_id: str,
    ac_id: str,
    caller: Principal,
    reason: str,
    risk: str,
    expires_at: datetime,
) -> Waiver:
    resolved = resolve_principal(caller)
    if not isinstance(resolved, Human):
        raise PrincipalNotAllowedError("only a human owner can request a waiver")
    sensitive_reason = find_sensitive_reason(reason, risk)
    if sensitive_reason is not None:
        raise SensitiveContentError(f"疑似包含敏感信息（{sensitive_reason}），拒绝记录")

    contract = get_without_audit(contract_id)
    if contract is None:
        raise ContractStateError(f"unknown contract_id {contract_id!r}")
    if contract.status != ContractStatus.FROZEN:
        # 豁免针对的是"某条已经冻结、内容不会再变的 AC"——草稿期 AC 内容
        # 还能被 update() 改掉，这时候批的豁免是针对哪个版本的 AC 说不
        # 清楚，人审批时看到的内容和最终冻结时的内容可能已经不是一回事。
        raise ContractStateError(
            f"contract_id {contract_id!r} is {contract.status.value}, waivers can only be "
            "requested for frozen contracts"
        )
    matching_ac = next((ac for ac in contract.acceptance_criteria if ac.ac_id == ac_id), None)
    if matching_ac is None:
        raise ContractStateError(f"contract {contract_id!r} 没有编号为 {ac_id!r} 的验收标准")
    if matching_ac.touches_production_or_irreversible:
        raise WaiverNotAllowedError(f"{ac_id} 涉及生产数据/不可逆操作，不允许豁免，必须真通过")

    now = _now()
    waiver = Waiver(
        waiver_id=uuid.uuid4().hex,
        contract_id=contract_id,
        ac_id=ac_id,
        reason=reason,
        risk=risk,
        approved_by=resolved.id,
        created_at=now,
        expires_at=expires_at,
    )
    principal_type, principal_id, session_id = _principal_type_and_id(resolved)
    with get_connection() as conn:
        contract_store.insert_waiver(conn, waiver)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now,
                principal_type=principal_type,
                principal_id=principal_id,
                session_id=session_id,
                action="contract.waiver.request",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"contract_id": contract_id, "ac_id": ac_id}),
                result_summary=f"waiver_id={waiver.waiver_id} expires_at={expires_at.isoformat()}",
            ),
        )
    return waiver


def is_ac_waived(contract_id: str, ac_id: str, *, now: datetime | None = None) -> bool:
    """给 harness 模块判定准出门禁时用——contract_id+ac_id 是否有一个
    当前未过期的豁免覆盖。不记审计（这是内部判定逻辑的一部分，判定结果
    会体现在 harness 那边写的审计事件里，这里单独记一条没有意义）。
    """
    moment = now if now is not None else _now()
    with get_connection() as conn:
        waivers = contract_store.list_waivers(conn, contract_id)
    return any(w.ac_id == ac_id and w.expires_at > moment for w in waivers)
