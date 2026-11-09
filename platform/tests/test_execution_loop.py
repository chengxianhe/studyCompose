from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gate_fixtures import make_receipt, make_repository

from govplatform.api.app import app
from govplatform.contract import service as contracts
from govplatform.contract.models import AcceptanceCriterion, VerificationCase, VerificationType
from govplatform.delivery.context import get_context, prepare
from govplatform.delivery.evidence import EvidenceError, evidence_summary, read_evidence
from govplatform.delivery.report import latest_packet
from govplatform.delivery.submission import submit
from govplatform.harness import service as harness
from govplatform.harness.models import AcceptanceResult, HarnessRun, HarnessStatus
from govplatform.identity.models import Agent, Human
from govplatform.mcp_server.server import harness_record_entry_gate


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return make_repository(tmp_path / "worktree")


@pytest.fixture
def run(codex_agent: Agent, owner_human: Human) -> HarnessRun:
    contract = contracts.create(
        title="闭环测试",
        goal="可接续",
        scope="测试仓库",
        caller=codex_agent,
        acceptance_criteria=[
            AcceptanceCriterion(
                ac_id=key,
                precondition="基线",
                action="检查",
                input="结果",
                expected_result="符合条件",
                verification_type=kind,
                test_case_ids=[key],
            )
            for key, kind in [
                ("auto", VerificationType.AUTOMATED_TEST),
                ("human", VerificationType.MANUAL_EVIDENCE),
            ]
        ],
        test_cases=[VerificationCase(tc_id=key, description="test") for key in ("auto", "human")],
    )
    contracts.freeze(contract_id=contract.contract_id, caller=owner_human)
    return harness.start(contract_id=contract.contract_id, caller=owner_human)


def admit(repo: Path, run: HarnessRun, caller: Agent) -> None:
    prepare(
        repository=repo,
        directory=make_receipt(repo),
        mode="platform",
        run_id=run.run_id,
        caller=caller,
    )


def auto_results() -> list[AcceptanceResult]:
    return [
        AcceptanceResult(ac_id="auto", passed=True, evidence_summary="isolated fixture checked")
    ]


def test_unstarted_and_failed_baseline_rejected(
    repo: Path, run: HarnessRun, codex_agent: Agent
) -> None:
    with pytest.raises(EvidenceError, match="用户启动"):
        prepare(
            repository=repo,
            directory=make_receipt(repo),
            mode="platform",
            run_id="not-started",
            caller=codex_agent,
        )
    with pytest.raises(EvidenceError, match="基线检查失败"):
        prepare(
            repository=repo,
            directory=make_receipt(repo, 1),
            mode="platform",
            run_id=run.run_id,
            caller=codex_agent,
        )
    assert get_context(run.run_id) is None


def test_prepare_is_immutable_and_preserves_existing_wip(
    repo: Path, run: HarnessRun, codex_agent: Agent
) -> None:
    (repo / "source.txt").write_text("prior WIP\n")
    (repo / "prior.txt").write_text("existing untracked\n")
    admit(repo, run, codex_agent)
    original = get_context(run.run_id)
    assert original is not None
    (repo / "source.txt").write_text("new work\n")
    resumed = prepare(
        repository=repo,
        directory=make_receipt(repo),
        mode="platform",
        run_id=run.run_id,
        caller=codex_agent,
    )
    assert resumed == original
    updated, packet = submit(
        run_id=run.run_id,
        directory=make_receipt(repo),
        results=auto_results(),
        limitations="未测真机",
        caller=codex_agent,
    )
    assert updated.status == HarnessStatus.WAITING_FOR_HUMAN
    assert updated.delivered_at is None
    patch = (packet / "changes.patch").read_text()
    assert "-prior WIP" in patch and "+new work" in patch
    assert "prior.txt" not in patch
    assert "未测真机" in (packet / "review.md").read_text()
    assert json.loads((packet / "report.json").read_text())["approval"] == "pending"
    assert latest_packet(run.run_id) == str(packet)
    with pytest.raises(EvidenceError, match="可提交状态"):
        submit(
            run_id=run.run_id,
            directory=make_receipt(repo),
            results=auto_results(),
            limitations="none",
            caller=codex_agent,
        )


def test_raw_boolean_cannot_bypass_admission(
    repo: Path, run: HarnessRun, codex_agent: Agent
) -> None:
    with pytest.raises(harness.HarnessStateError, match="缺少准入"):
        harness.record_entry_gate(
            run_id=run.run_id, caller=codex_agent, passed=True, command="test", summary="ok"
        )
    admit(repo, run, codex_agent)
    with pytest.raises(harness.HarnessStateError, match="证据无效"):
        harness.record_entry_gate(
            run_id=run.run_id, caller=codex_agent, passed=True, command="test", summary="ok"
        )
    current = harness.get(run.run_id, caller=codex_agent)
    assert current is not None and current.status == HarnessStatus.DEVELOPING


@pytest.mark.parametrize("case", ["failed_claim", "mode", "source", "snapshot"])
def test_gate_rejects_mismatch(repo: Path, run: HarnessRun, codex_agent: Agent, case: str) -> None:
    admit(repo, run, codex_agent)
    directory = make_receipt(repo, 1 if case == "failed_claim" else 0)
    evidence = read_evidence(repo, directory, "platform")
    if case == "mode":
        (directory / "mode.txt").write_text("android")
    elif case == "source":
        (repo / "source.txt").write_text("modified")
    elif case == "snapshot":
        context = get_context(run.run_id)
        assert context is not None
        Path(context.snapshot).write_text("{}")
    with pytest.raises(harness.HarnessStateError, match="证据无效"):
        harness.record_entry_gate(
            run_id=run.run_id,
            caller=codex_agent,
            passed=True,
            command="bash scripts/verify.sh platform",
            summary=evidence_summary(evidence),
        )


def test_failed_verification_does_not_pass_or_record_acs(
    repo: Path, run: HarnessRun, codex_agent: Agent
) -> None:
    admit(repo, run, codex_agent)
    updated, packet = submit(
        run_id=run.run_id,
        directory=make_receipt(repo, 1),
        results=auto_results(),
        limitations="统一检查失败",
        caller=codex_agent,
    )
    assert updated.status == HarnessStatus.DEVELOPING
    assert updated.acceptance_results == []
    assert updated.entry_gate_results[-1].passed is False
    assert json.loads((packet / "outcome.json").read_text())["status"] == "developing"


def test_manual_failure_can_reopen_stale_work_but_old_receipt_cannot_pass(
    repo: Path, run: HarnessRun, codex_agent: Agent, owner_human: Human
) -> None:
    admit(repo, run, codex_agent)
    directory = make_receipt(repo)
    waiting, _ = submit(
        run_id=run.run_id,
        directory=directory,
        results=auto_results(),
        limitations="none",
        caller=codex_agent,
    )
    (repo / "source.txt").write_text("edited after review packet")
    with pytest.raises(harness.HarnessStateError, match="证据无效"):
        harness.record_acceptance(
            run_id=run.run_id,
            caller=owner_human,
            results=[AcceptanceResult(ac_id="human", passed=True, evidence_summary="looks good")],
            manual_only=True,
        )
    failed = harness.record_acceptance(
        run_id=waiting.run_id,
        caller=owner_human,
        results=[AcceptanceResult(ac_id="human", passed=False, evidence_summary="needs fix")],
        manual_only=True,
    )
    assert failed.status == HarnessStatus.REPAIRING
    # Even if the code is restored, a previous round's evidence cannot be reused.
    (repo / "source.txt").write_text("source\n")
    with pytest.raises(harness.HarnessStateError, match="此前验收"):
        submit(
            run_id=run.run_id,
            directory=directory,
            results=auto_results(),
            limitations="none",
            caller=codex_agent,
        )
    fresh, _ = submit(
        run_id=run.run_id,
        directory=make_receipt(repo),
        results=auto_results(),
        limitations="none",
        caller=codex_agent,
    )
    assert fresh.status == HarnessStatus.WAITING_FOR_HUMAN
    assert all(r.round_number == 1 for r in fresh.acceptance_results[-1:])


def test_no_manual_self_approval_and_no_missing_auto_ac(
    repo: Path, run: HarnessRun, codex_agent: Agent
) -> None:
    admit(repo, run, codex_agent)
    for results in [
        [],
        [*auto_results(), AcceptanceResult(ac_id="human", passed=True, evidence_summary="self")],
    ]:
        with pytest.raises(EvidenceError, match="全部非人工"):
            submit(
                run_id=run.run_id,
                directory=make_receipt(repo),
                results=results,
                limitations="none",
                caller=codex_agent,
            )


def test_http_entry_gate_uses_common_guard(run: HarnessRun, codex_agent: Agent) -> None:
    response = TestClient(app).post(
        f"/harness-runs/{run.run_id}/entry-gate",
        json={
            "caller": codex_agent.model_dump(),
            "passed": True,
            "command": "test",
            "summary": "ok",
        },
    )
    assert response.status_code == 400
    assert "准入" in response.text


@pytest.mark.asyncio
async def test_mcp_entry_gate_uses_common_guard(run: HarnessRun, codex_agent: Agent) -> None:
    with pytest.raises(harness.HarnessStateError, match="准入"):
        await harness_record_entry_gate(run.run_id, codex_agent, True, "test", "ok")


def test_cli_prepare_submit_and_resume(repo: Path, run: HarnessRun, codex_agent: Agent) -> None:
    def cli(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "govplatform.delivery",
                *args,
                "--run-id",
                run.run_id,
                "--session-id",
                codex_agent.session_id,
            ],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

    receipt = make_receipt(repo)
    admitted = cli("prepare", "--repo", str(repo), "--mode", "platform", "--evidence", str(receipt))
    assert admitted.returncode == 0, admitted.stdout + admitted.stderr
    wrong_mode = cli("verify", "--repo", str(repo), "--mode", "all")
    assert wrong_mode.returncode == 2 and "未执行验证命令" in wrong_mode.stderr
    (repo / "new.txt").write_text("new untracked work\n")
    result_file = repo / ".verification/results.json"
    result_file.write_text(json.dumps([r.model_dump(mode="json") for r in auto_results()]))
    submitted = cli(
        "submit",
        "--evidence",
        str(make_receipt(repo)),
        "--results",
        str(result_file),
        "--limitations",
        "真机未验证",
    )
    assert submitted.returncode == 0, submitted.stdout + submitted.stderr
    assert "waiting_for_human" in submitted.stdout
    status = cli("status")
    assert status.returncode == 0 and "waiting_for_human" in status.stdout
    packet_path = latest_packet(run.run_id)
    assert packet_path is not None and packet_path in status.stdout
    packet = Path(packet_path)
    assert "+new untracked work" in (packet / "changes.patch").read_text()
    assert cli("prepare", "--repo", str(repo), "--mode", "platform").returncode == 2


def test_approved_source_change_blocks_delivery(
    repo: Path, run: HarnessRun, codex_agent: Agent, owner_human: Human
) -> None:
    admit(repo, run, codex_agent)
    submit(
        run_id=run.run_id,
        directory=make_receipt(repo),
        results=auto_results(),
        limitations="none",
        caller=codex_agent,
    )
    accepted = harness.record_acceptance(
        run_id=run.run_id,
        caller=owner_human,
        results=[AcceptanceResult(ac_id="human", passed=True, evidence_summary="reviewed")],
        manual_only=True,
    )
    assert accepted.status == HarnessStatus.PASSED
    (repo / "source.txt").write_text("changed after approval")
    with pytest.raises(harness.HarnessStateError, match="证据无效"):
        harness.deliver(run_id=run.run_id, caller=owner_human)


def test_binding_cannot_be_changed(repo: Path, run: HarnessRun, codex_agent: Agent) -> None:
    admit(repo, run, codex_agent)
    with pytest.raises(EvidenceError, match="其他仓库或验证范围"):
        prepare(
            repository=repo,
            directory=make_receipt(repo),
            mode="all",
            run_id=run.run_id,
            caller=codex_agent,
        )
