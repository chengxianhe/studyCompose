"""契约模块对外唯一入口。

实际实现按操作拆成了几个文件（`_shared.py`/`update_service.py`/
`freeze_service.py`/`waiver_service.py`）——单个文件超过了项目 250 行的
上限，拆分详见 `_shared.py` 顶部注释。这里全部重新导出，外部调用方
（`api/routes/`、`mcp_server/`、`harness/`、测试）继续用
`from govplatform.contract import service as contract_service` 然后
`contract_service.create/update/freeze/get/request_waiver/is_ac_waived`，
或者 `from govplatform.contract.service import XxxError`，不用改任何
import。
"""

from __future__ import annotations

import json
import uuid

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.contract import store as contract_store
from govplatform.contract._shared import (
    ContractConflictError as ContractConflictError,
)
from govplatform.contract._shared import (
    ContractStateError as ContractStateError,
)
from govplatform.contract._shared import (
    SensitiveContentError as SensitiveContentError,
)
from govplatform.contract._shared import get_without_audit as get_without_audit
from govplatform.contract._shared import now as _now
from govplatform.contract._shared import principal_type_and_id as _principal_type_and_id
from govplatform.contract._shared import sensitive_reason_in_contract as _sensitive_reason
from govplatform.contract.freeze_service import (
    ContractValidationError as ContractValidationError,
)
from govplatform.contract.freeze_service import freeze as freeze
from govplatform.contract.models import (
    AcceptanceCriterion,
    Contract,
    ContractStatus,
    VerificationCase,
)
from govplatform.contract.update_service import update as update
from govplatform.contract.waiver_service import (
    InvalidWaiverError as InvalidWaiverError,
)
from govplatform.contract.waiver_service import (
    WaiverNotAllowedError as WaiverNotAllowedError,
)
from govplatform.contract.waiver_service import is_ac_waived as is_ac_waived
from govplatform.contract.waiver_service import request_waiver as request_waiver
from govplatform.db.connection import get_connection
from govplatform.identity.models import Principal, resolve_principal

__all__ = [
    "Contract",
    "ContractConflictError",
    "ContractStateError",
    "ContractValidationError",
    "InvalidWaiverError",
    "SensitiveContentError",
    "WaiverNotAllowedError",
    "create",
    "freeze",
    "get",
    "get_without_audit",
    "is_ac_waived",
    "request_waiver",
    "update",
]


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

    reason = _sensitive_reason(
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

    moment = _now()
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
        created_at=moment,
        updated_at=moment,
    )
    with get_connection() as conn:
        contract_store.insert(conn, contract)
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=moment,
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
