from __future__ import annotations

import json

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.contract import store as contract_store
from govplatform.contract._shared import (
    ContractStateError,
    get_without_audit,
    now,
    principal_type_and_id,
)
from govplatform.contract.models import Contract, ContractStatus, KnowledgeSnapshot
from govplatform.db.connection import get_connection
from govplatform.identity.models import (
    Human,
    Principal,
    PrincipalNotAllowedError,
    resolve_principal,
)
from govplatform.knowledge import service as knowledge_service


class ContractValidationError(Exception):
    """freeze() 时结构校验不通过（AC/TC 引用不完整、待澄清问题未清空等）时抛出。"""


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

    # 对应需求准入门禁调研（GitHub spec-kit 的 "[NEEDS CLARIFICATION]"
    # 机制）：待澄清问题清零之前不允许冻结，不能带着没想清楚的模糊点往下
    # 走。open_questions 之前只是个自由字段，没人真的检查它是不是空的。
    if contract.open_questions:
        errors.append(
            f"open_questions 还有 {len(contract.open_questions)} 条未解决，"
            "必须清空（问清楚/写进 AC/明确排除）才能冻结"
        )

    # knowledge_service.get() 自己管理连接，这里不复用 freeze() 已经打开
    # 的那个——SQLite 支持同一个文件的多个只读连接同时存在，简单起见不去
    # 传递/复用底层连接对象。
    snapshots: list[KnowledgeSnapshot] = []
    moment = now()
    for knowledge_id in contract.knowledge_refs:
        knowledge = knowledge_service.get(knowledge_id)
        if knowledge is None:
            errors.append(f"knowledge_refs 引用了不存在的知识：{knowledge_id}")
        elif not knowledge_service.is_currently_valid(knowledge, now=moment):
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
    moment = now()
    principal_type, principal_id, session_id = principal_type_and_id(resolved)

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
                    occurred_at=moment,
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
            "frozen_at": moment,
            "updated_at": moment,
        }
    )
    with get_connection() as conn:
        contract_store.update(conn, frozen)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=moment,
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
