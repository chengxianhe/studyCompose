from __future__ import annotations

from pathlib import Path

from govplatform.contract import service as contracts
from govplatform.contract.models import VerificationType
from govplatform.delivery.context import get_context
from govplatform.delivery.evidence import EvidenceError, VerificationEvidence, read_evidence
from govplatform.delivery.report import record_outcome, register_packet, review_packet
from govplatform.delivery.service import import_verification
from govplatform.harness import service as harness
from govplatform.harness.evidence_guard import validate_current, validate_gate
from govplatform.harness.models import AcceptanceResult, HarnessRun, HarnessStatus
from govplatform.identity.models import Agent


def submit(
    *,
    run_id: str,
    directory: Path,
    results: list[AcceptanceResult],
    limitations: str,
    caller: Agent,
) -> tuple[HarnessRun, Path]:
    run = harness.get(run_id, caller=caller)
    context = get_context(run_id)
    if run is None or context is None:
        raise EvidenceError("运行或准入记录不存在")
    contract = contracts.get_without_audit(run.contract_id)
    assert contract is not None
    if run.status not in (
        HarnessStatus.DEVELOPING,
        HarnessStatus.REPAIRING,
        HarnessStatus.ACCEPTING,
    ):
        raise EvidenceError("运行不处于可提交状态；请用 status 查看或由人工反馈后继续")
    expected = {
        ac.ac_id
        for ac in contract.acceptance_criteria
        if ac.verification_type != VerificationType.MANUAL_EVIDENCE
    }
    if len({r.ac_id for r in results}) != len(results) or {r.ac_id for r in results} != expected:
        raise EvidenceError("须逐项提交全部非人工 AC，不能重复、遗漏或代填人工项")
    if not limitations.strip() or any(not r.evidence_summary.strip() for r in results):
        raise EvidenceError("必须填写逐项证据与未验证项说明（没有则明确说明）")
    evidence = read_evidence(Path(context.repository), directory, context.mode)
    if run.status == HarnessStatus.ACCEPTING:
        validate_current(run)
        if VerificationEvidence.model_validate_json(run.entry_gate_results[-1].summary) != evidence:
            raise EvidenceError("已有准出证据与本次提交不一致")
    else:
        validate_gate(
            run,
            evidence.exit_code == 0,
            f"bash scripts/verify.sh {context.mode}",
            evidence.model_dump_json(),
        )
    folder = review_packet(context, contract, evidence, results, limitations)
    register_packet(folder, run_id, caller)
    if run.status != HarnessStatus.ACCEPTING:
        run = import_verification(
            repository=Path(context.repository),
            directory=directory,
            mode=context.mode,
            run_id=run_id,
            caller=caller,
        )
    if evidence.exit_code == 0:
        linked_results = [
            r.model_copy(
                update={"evidence_summary": f"{r.evidence_summary}\n审查包：{folder / 'review.md'}"}
            )
            for r in results
        ]
        run = harness.record_acceptance(
            run_id=run_id,
            caller=caller,
            results=linked_results,
            expected_updated_at=run.updated_at,
        )
    record_outcome(folder, run)
    return run, folder
