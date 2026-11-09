"""The common guard used by CLI, HTTP and MCP state transitions."""

from pathlib import Path

from govplatform.delivery.context import get_context, read_snapshot
from govplatform.delivery.evidence import EvidenceError, VerificationEvidence, read_evidence
from govplatform.harness._shared import HarnessStateError
from govplatform.harness.models import HarnessRun


def validate_gate(run: HarnessRun, passed: bool, command: str, summary: str) -> None:
    try:
        context = get_context(run.run_id)
        if context is None:
            raise EvidenceError("缺少准入基线；先执行 delivery prepare")
        read_snapshot(context)
        claimed = VerificationEvidence.model_validate_json(summary)
        actual = read_evidence(Path(context.repository), Path(claimed.directory), context.mode)
        if actual != claimed or passed != (actual.exit_code == 0):
            raise EvidenceError("门禁声明与真实证据不一致")
        if command != f"bash scripts/verify.sh {context.mode}":
            raise EvidenceError("门禁命令与已绑定范围不一致")
        if actual.head != context.baseline.head:
            raise EvidenceError("HEAD 已变化，需重新确认任务基线")
        for gate in run.entry_gate_results:
            if not gate.passed:
                continue
            try:
                previous = VerificationEvidence.model_validate_json(gate.summary)
            except ValueError:
                # Legacy summaries remain history, never evidence for a new transition.
                continue
            if previous.directory == actual.directory:
                raise EvidenceError("该证据已用于此前验收，修复后须生成新证据")
    except (ValueError, OSError) as exc:
        raise HarnessStateError(f"门禁证据无效：{exc}") from exc


def validate_current(run: HarnessRun) -> None:
    if not run.entry_gate_results or not run.entry_gate_results[-1].passed:
        raise HarnessStateError("缺少已通过的门禁证据")
    gate = run.entry_gate_results[-1]
    # Exclude this gate from duplicate detection; still check source freshness.
    validate_gate(
        run.model_copy(update={"entry_gate_results": []}), True, gate.command, gate.summary
    )
