"""人工补审只沿用当前轮次有可信来源的结果，不把 Agent 自报当人工批准。"""

from govplatform.contract.models import Contract, VerificationType
from govplatform.harness._shared import HarnessStateError
from govplatform.harness.models import AcceptanceResult, HarnessRun
from govplatform.identity.models import Human
from govplatform.knowledge.sensitive import find_sensitive_reason


def merge_manual_results(
    run: HarnessRun,
    contract: Contract,
    incoming: list[AcceptanceResult],
) -> list[AcceptanceResult]:
    manual_ids = {
        ac.ac_id
        for ac in contract.acceptance_criteria
        if ac.verification_type == VerificationType.MANUAL_EVIDENCE
    }
    if not incoming:
        raise HarnessStateError("至少填写一条人工验收结论")
    for result in incoming:
        if result.ac_id not in manual_ids:
            raise HarnessStateError("人工补审入口只能提交人工 AC，自动结果由执行者记录")
        if not result.evidence_summary.strip() or len(result.evidence_summary) > 4000:
            raise HarnessStateError("请填写 1 至 4000 字的验证方法、实际结果和证据")
        if find_sensitive_reason(result.evidence_summary):
            raise HarnessStateError("证据疑似包含敏感信息，请脱敏后提交")
    current: dict[str, AcceptanceResult] = {}
    for result in run.acceptance_results:
        if result.round_number != run.repair_round:
            continue
        current[result.ac_id] = result
    # 最新一条若不可信，不得退回更早的成功结果。
    current = {
        key: value
        for key, value in current.items()
        if key not in manual_ids or isinstance(value.recorded_by, Human)
    }
    current.update({result.ac_id: result for result in incoming})
    return list(current.values())
