from __future__ import annotations

import json
import uuid
from datetime import datetime

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.contract import store as contract_store
from govplatform.contract._shared import (
    ContractStateError,
    SensitiveContentError,
    get_without_audit,
    principal_type_and_id,
)
from govplatform.contract._shared import now as _now
from govplatform.contract.models import ContractStatus, Waiver
from govplatform.db.connection import get_connection
from govplatform.identity.models import (
    Human,
    Principal,
    PrincipalNotAllowedError,
    resolve_principal,
)
from govplatform.knowledge.sensitive import find_sensitive_reason


class WaiverNotAllowedError(Exception):
    """request_waiver() 针对 touches_production_or_irreversible 的 AC 时抛出。

    对应 baseline 文档 §7.3 从 Anthropic 自己公开实践调研来的限制：
    涉及生产数据/不可逆操作的验收标准，没有豁免这条路，必须真通过。
    """


class InvalidWaiverError(Exception):
    """request_waiver() 的 expires_at 不合法时抛出——必须带时区信息、且
    必须晚于当前时刻。

    is_ac_waived() 拿 expires_at 跟 UTC 时间比较，如果传进来的是 naive
    datetime（没有 tzinfo），Python 会直接抛 TypeError（aware/naive 不能
    互相比较），而不是给出清楚的拒绝原因；如果传进来的时间已经过去，会
    造出一个一创建就永远无效的豁免对象，留在审计记录里但没有任何实际
    作用。两种都在创建时就直接拒绝，不留到用的时候才炸。
    """


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
    if expires_at.tzinfo is None:
        raise InvalidWaiverError("expires_at 必须带时区信息（不能是 naive datetime）")
    if expires_at <= _now():
        raise InvalidWaiverError("expires_at 必须晚于当前时间——不允许创建一开始就过期的豁免")
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

    moment = _now()
    waiver = Waiver(
        waiver_id=uuid.uuid4().hex,
        contract_id=contract_id,
        ac_id=ac_id,
        reason=reason,
        risk=risk,
        approved_by=resolved.id,
        created_at=moment,
        expires_at=expires_at,
    )
    principal_type, principal_id, session_id = principal_type_and_id(resolved)
    with get_connection() as conn:
        contract_store.insert_waiver(conn, waiver)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=moment,
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
