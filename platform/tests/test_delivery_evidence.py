from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from govplatform.contract import service as contracts
from govplatform.contract.models import AcceptanceCriterion, VerificationCase, VerificationType
from govplatform.delivery.context import prepare
from govplatform.delivery.evidence import EvidenceError, current_fingerprint, read_evidence
from govplatform.delivery.service import import_verification
from govplatform.harness import service as harness
from govplatform.harness.models import HarnessRun, HarnessStatus
from govplatform.identity.models import Agent, Human


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / ".gitignore").write_text(".verification/\n")
    (root / "source.txt").write_text("source\n")
    shutil.copy2(
        Path(__file__).resolve().parents[2] / "scripts/workspace_fingerprint.py",
        root / "scripts/workspace_fingerprint.py",
    )
    for args in (
        ("init", "-q"),
        ("add", "."),
        ("-c", "user.name=Test", "-c", "user.email=test@example.test", "commit", "-qm", "init"),
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    return root


def receipt(root: Path, exit_code: int = 0) -> Path:
    directory = root / ".verification/platform.fixture"
    directory.mkdir(parents=True, exist_ok=True)
    fingerprint = current_fingerprint(root)
    for name, value in {
        "mode.txt": "platform",
        "exit-code.txt": str(exit_code),
        "head.txt": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True),
        "fingerprint-before.txt": fingerprint,
        "fingerprint-after.txt": fingerprint,
        "output.log": "fixture verification output",
        "status.txt": "",
    }.items():
        (directory / name).write_text(value)
    return directory


@pytest.fixture
def developing(codex_agent: Agent, owner_human: Human, repository: Path) -> HarnessRun:
    contract = contracts.create(
        title="证据导入测试",
        goal="验证",
        scope="fixture",
        caller=codex_agent,
        acceptance_criteria=[
            AcceptanceCriterion(
                ac_id="manual",
                precondition="自动检查通过",
                action="人工审核",
                input="证据",
                expected_result="符合要求",
                verification_type=VerificationType.MANUAL_EVIDENCE,
                test_case_ids=["TC"],
            )
        ],
        test_cases=[VerificationCase(tc_id="TC", description="fixture")],
    )
    contracts.freeze(contract_id=contract.contract_id, caller=owner_human)
    run = harness.start(contract_id=contract.contract_id, caller=owner_human)
    prepare(
        repository=repository,
        directory=receipt(repository),
        mode="platform",
        run_id=run.run_id,
        caller=codex_agent,
    )
    return run


@pytest.mark.parametrize("exit_code", [0, 1])
def test_import_preserves_result_and_does_not_accept_manual(
    repository: Path,
    developing: HarnessRun,
    codex_agent: Agent,
    exit_code: int,
) -> None:
    directory = receipt(repository, exit_code)
    updated = import_verification(
        repository=repository,
        directory=directory,
        mode="platform",
        run_id=developing.run_id,
        caller=codex_agent,
    )
    assert updated.status == (
        HarnessStatus.ACCEPTING if exit_code == 0 else HarnessStatus.DEVELOPING
    )
    assert updated.acceptance_results == []
    data = json.loads(updated.entry_gate_results[-1].summary)
    assert data["exit_code"] == exit_code and len(data["log_sha256"]) == 64


@pytest.mark.parametrize(
    "change",
    ["source", "mode", "unfinished", "changed_during_run", "empty_log", "bad_exit", "symlink"],
)
def test_invalid_evidence_rejected(repository: Path, change: str) -> None:
    directory = receipt(repository)
    if change == "source":
        (repository / "source.txt").write_text("changed")
    elif change == "mode":
        (directory / "mode.txt").write_text("workflow")
    elif change == "unfinished":
        (directory / "exit-code.txt").unlink()
    elif change == "changed_during_run":
        (directory / "fingerprint-before.txt").write_text("old")
    elif change == "empty_log":
        (directory / "output.log").write_text("")
    elif change == "bad_exit":
        (directory / "exit-code.txt").write_text("unknown")
    else:
        (directory / "output.log").unlink()
        (directory / "output.log").symlink_to(repository / "source.txt")
    with pytest.raises(EvidenceError):
        read_evidence(repository, directory, "platform")


def test_cli_verify_preserves_failed_exit(
    repository: Path, developing: HarnessRun, codex_agent: Agent
) -> None:
    directory = repository / ".verification/platform.fixture"
    # 可控验证命令，仅为测试进程退出码传播；不冒充真实项目门禁。
    (repository / "scripts/verify.sh").write_text(
        '#!/bin/sh\necho "Verification: platform; evidence: ' + str(directory) + '"\nexit 1\n'
    )
    receipt(repository, 1)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "govplatform.delivery",
            "verify",
            "--repo",
            str(repository),
            "--mode",
            "platform",
            "--run-id",
            developing.run_id,
            "--session-id",
            "test-cli",
        ],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    assert result.returncode == 1, result.stdout + result.stderr
    run = harness.get(developing.run_id, caller=codex_agent)
    assert run is not None and run.status == HarnessStatus.DEVELOPING
    assert run.entry_gate_results[-1].passed is False
