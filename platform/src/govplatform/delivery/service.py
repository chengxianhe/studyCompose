from pathlib import Path

from govplatform.delivery.evidence import VerificationMode, evidence_summary, read_evidence
from govplatform.harness import service as harness
from govplatform.harness.models import HarnessRun
from govplatform.identity.models import Agent, resolve_principal


def import_verification(
    *,
    repository: Path,
    directory: Path,
    mode: VerificationMode,
    run_id: str,
    caller: Agent,
) -> HarnessRun:
    resolve_principal(caller)
    evidence = read_evidence(repository, directory, mode)
    return harness.record_entry_gate(
        run_id=run_id,
        caller=caller,
        passed=evidence.exit_code == 0,
        command=f"bash scripts/verify.sh {mode}",
        summary=evidence_summary(evidence),
    )
