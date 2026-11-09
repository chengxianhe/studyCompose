"""Real temporary Git/evidence files for state-machine tests; no production records."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

from govplatform.config import db_path
from govplatform.delivery.context import get_context, prepare
from govplatform.delivery.evidence import current_fingerprint, evidence_summary, read_evidence
from govplatform.harness import service
from govplatform.harness.models import HarnessRun
from govplatform.identity.models import Agent


def make_repository(root: Path) -> Path:
    (root / "scripts").mkdir(parents=True)
    (root / ".gitignore").write_text(".verification/\n")
    (root / "source.txt").write_text("source\n")
    shutil.copy2(
        Path(__file__).resolve().parents[2] / "scripts/workspace_fingerprint.py",
        root / "scripts/workspace_fingerprint.py",
    )
    for args in [
        ("init", "-q"),
        ("add", "."),
        ("-c", "user.name=Test", "-c", "user.email=test@example.test", "commit", "-qm", "init"),
    ]:
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    return root


def make_receipt(root: Path, exit_code: int = 0) -> Path:
    directory = root / ".verification" / f"platform.{uuid.uuid4().hex}"
    directory.mkdir(parents=True)
    fingerprint = current_fingerprint(root)
    for name, value in {
        "mode.txt": "platform",
        "exit-code.txt": str(exit_code),
        "head.txt": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True),
        "fingerprint-before.txt": fingerprint,
        "fingerprint-after.txt": fingerprint,
        "output.log": "Isolated test fixture; not a real project verification",
        "status.txt": "",
    }.items():
        (directory / name).write_text(value)
    return directory


def record_fixture_gate(
    *,
    run_id: str,
    caller: Agent,
    passed: bool,
    command: str,
    summary: str,
) -> HarnessRun:
    # Existing tests retain their state-machine assertions; supply the now-required evidence.
    context = get_context(run_id)
    if context is None:
        root = make_repository(db_path().parent / f"repo-{run_id}")
        prepare(
            repository=root,
            directory=make_receipt(root),
            mode="platform",
            run_id=run_id,
            caller=caller,
        )
    else:
        root = Path(context.repository)
    directory = make_receipt(root, 0 if passed else 1)
    return service.record_entry_gate(
        run_id=run_id,
        caller=caller,
        passed=passed,
        command="bash scripts/verify.sh platform",
        summary=evidence_summary(read_evidence(root, directory, "platform")),
    )
