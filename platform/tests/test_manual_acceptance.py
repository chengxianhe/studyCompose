from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from gate_fixtures import record_fixture_gate

from govplatform.contract import service as contracts
from govplatform.contract.models import AcceptanceCriterion, VerificationCase, VerificationType
from govplatform.harness import acceptance_service, service, store
from govplatform.harness.models import AcceptanceResult, HarnessRun, HarnessStatus
from govplatform.identity.models import Agent, Human, PrincipalNotAllowedError
from govplatform.review.app import create_review_app


@pytest.fixture
def waiting_run(codex_agent: Agent, owner_human: Human) -> HarnessRun:
    contract = contracts.create(
        title="人工验收测试",
        goal="验收",
        scope="隔离库",
        caller=codex_agent,
        acceptance_criteria=[
            AcceptanceCriterion(
                ac_id=key,
                precondition="已验证",
                action="审核",
                input="证据",
                expected_result="正确",
                verification_type=kind,
                test_case_ids=["TC"],
            )
            for key, kind in (
                ("auto", VerificationType.AUTOMATED_TEST),
                ("manual1", VerificationType.MANUAL_EVIDENCE),
                ("manual2", VerificationType.MANUAL_EVIDENCE),
            )
        ],
        test_cases=[VerificationCase(tc_id="TC", description="测试")],
    )
    contracts.freeze(contract_id=contract.contract_id, caller=owner_human)
    run = service.start(contract_id=contract.contract_id, caller=owner_human)
    record_fixture_gate(
        run_id=run.run_id, caller=codex_agent, passed=True, command="test", summary="ok"
    )
    return service.record_acceptance(
        run_id=run.run_id,
        caller=codex_agent,
        results=[
            AcceptanceResult(ac_id="auto", passed=True, evidence_summary="自动测试通过"),
            AcceptanceResult(
                ac_id="manual2",
                passed=True,
                evidence_summary="Agent 不能自证人工项",
                recorded_by=owner_human,
            ),
        ],
    )


def fields_for(client: TestClient, action: str) -> dict[str, str]:
    matched = re.search(
        rf'<form method="post" action="{action}">(.*?)</form>', client.get("/tasks").text, re.S
    )
    assert matched is not None
    return dict(re.findall(r'name="([^"]+)" value="([^"]+)"', matched[1]))


def test_partial_manual_review_preserves_provenance(
    waiting_run: HarnessRun, codex_agent: Agent
) -> None:
    assert waiting_run.status == HarnessStatus.WAITING_FOR_HUMAN
    assert isinstance(waiting_run.acceptance_results[-1].recorded_by, Agent)
    action = f"/actions/accept/{waiting_run.run_id}"
    with TestClient(
        create_review_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 1)
    ) as client:
        fields = fields_for(client, action)
        assert (
            client.post(
                action,
                data={**fields, "decision_1": "pass", "evidence_1": "亲自检查第一项截图"},
                follow_redirects=False,
            ).status_code
            == 303
        )
        after = service.get(waiting_run.run_id, caller=codex_agent)
        assert after is not None and after.status == HarnessStatus.WAITING_FOR_HUMAN
        assert isinstance(after.acceptance_results[0].recorded_by, Agent)
        assert isinstance(after.acceptance_results[-1].recorded_by, Human)
        assert len(after.acceptance_results) == 3  # 不把沿用的自动证据改写为 Human
        assert client.post(action, data=fields).status_code == 409
        fields = fields_for(client, action)
        assert (
            client.post(
                action,
                data={**fields, "decision_2": "pass", "evidence_2": "亲自验证第二项"},
                follow_redirects=False,
            ).status_code
            == 303
        )
        final = service.get(waiting_run.run_id, caller=codex_agent)
        assert final is not None and final.status == HarnessStatus.PASSED


def test_manual_failure_requires_repair_and_previous_round_not_reused(
    waiting_run: HarnessRun,
    codex_agent: Agent,
    owner_human: Human,
) -> None:
    failed = service.record_acceptance(
        run_id=waiting_run.run_id,
        caller=owner_human,
        manual_only=True,
        results=[
            AcceptanceResult(ac_id="manual1", passed=False, evidence_summary="截图不符合预期")
        ],
    )
    assert failed.status == HarnessStatus.REPAIRING and failed.repair_round == 1
    record_fixture_gate(
        run_id=failed.run_id, caller=codex_agent, passed=True, command="test", summary="修复后通过"
    )
    # 旧轮次 auto 即使通过，也不能被这轮人工审核捡回来。
    next_round = service.record_acceptance(
        run_id=failed.run_id,
        caller=owner_human,
        manual_only=True,
        results=[AcceptanceResult(ac_id="manual1", passed=True, evidence_summary="修复项已确认")],
    )
    assert next_round.status == HarnessStatus.REPAIRING


def test_manual_input_guards(
    waiting_run: HarnessRun, codex_agent: Agent, owner_human: Human
) -> None:
    with pytest.raises(PrincipalNotAllowedError):
        service.record_acceptance(
            run_id=waiting_run.run_id, caller=codex_agent, results=[], manual_only=True
        )
    for key, evidence in (
        ("auto", "不得覆盖自动结果"),
        ("manual1", " "),
        ("manual1", "password=secret"),
    ):
        with pytest.raises(service.HarnessStateError):
            service.record_acceptance(
                run_id=waiting_run.run_id,
                caller=owner_human,
                manual_only=True,
                results=[AcceptanceResult(ac_id=key, passed=True, evidence_summary=evidence)],
            )
    with TestClient(
        create_review_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 1)
    ) as client:
        action = f"/actions/accept/{waiting_run.run_id}"
        fields = fields_for(client, action)
        assert client.post(action, data={**fields, "decision_1": "pass"}).status_code == 422
        fields = fields_for(client, action)
        assert (
            client.post(
                action,
                data={**fields, "decision_1": "pass", "evidence_1": "checked"},
                headers={"Origin": "https://evil.test"},
            ).status_code
            == 403
        )


def test_manual_write_cannot_overwrite_concurrent_result(
    waiting_run: HarnessRun,
    owner_human: Human,
    codex_agent: Agent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = store.update

    def raced(
        conn: sqlite3.Connection,
        run: HarnessRun,
        *,
        expected_updated_at: datetime,
    ) -> bool:
        monkeypatch.setattr(acceptance_service, "harness_store", store)
        service.record_acceptance(
            run_id=run.run_id,
            caller=owner_human,
            manual_only=True,
            results=[AcceptanceResult(ac_id="manual2", passed=True, evidence_summary="并发审核")],
        )
        return original(conn, run, expected_updated_at=expected_updated_at)

    monkeypatch.setattr(
        acceptance_service, "harness_store", SimpleNamespace(get=store.get, update=raced)
    )
    with pytest.raises(service.HarnessStateError):
        service.record_acceptance(
            run_id=waiting_run.run_id,
            caller=owner_human,
            manual_only=True,
            results=[AcceptanceResult(ac_id="manual1", passed=True, evidence_summary="过期审核")],
        )
    current = service.get(waiting_run.run_id, caller=codex_agent)
    assert current is not None and current.acceptance_results[-1].ac_id == "manual2"
