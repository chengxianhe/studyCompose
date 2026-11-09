from concurrent.futures import ThreadPoolExecutor

import pytest
from gate_fixtures import record_fixture_gate

from govplatform.contract import service as contracts
from govplatform.contract.models import AcceptanceCriterion, VerificationCase, VerificationType
from govplatform.harness import service as harness
from govplatform.harness.cancellation_service import cancel
from govplatform.harness.models import HarnessStatus
from govplatform.identity.models import Agent, Human, PrincipalNotAllowedError


@pytest.fixture
def frozen_id(codex_agent: Agent, owner_human: Human) -> str:
    contract = contracts.create(
        title="启动并发测试",
        goal="目标",
        scope="测试",
        caller=codex_agent,
        acceptance_criteria=[
            AcceptanceCriterion(
                ac_id="AC",
                precondition="ready",
                action="test",
                input="fixture",
                expected_result="pass",
                verification_type=VerificationType.BUILD_LOG,
                test_case_ids=["TC"],
            )
        ],
        test_cases=[VerificationCase(tc_id="TC", description="test")],
    )
    contracts.freeze(contract_id=contract.contract_id, caller=owner_human)
    return contract.contract_id


def test_cancel_preserves_history_and_allows_new_run(
    frozen_id: str, codex_agent: Agent, owner_human: Human
) -> None:
    run = harness.start(contract_id=frozen_id, caller=owner_human)
    record_fixture_gate(
        run_id=run.run_id, caller=codex_agent, passed=False, command="test", summary="failed"
    )
    with pytest.raises(PrincipalNotAllowedError):
        cancel(run_id=run.run_id, caller=codex_agent, reason="agent must not cancel")
    with pytest.raises(harness.HarnessStateError):
        cancel(run_id=run.run_id, caller=owner_human, reason=" ")
    with pytest.raises(harness.HarnessStateError):
        cancel(
            run_id=run.run_id,
            caller=owner_human,
            reason="旧页面",
            expected_updated_at=run.updated_at,
        )
    cancelled = cancel(run_id=run.run_id, caller=owner_human, reason="误启动")
    assert cancelled.status == HarnessStatus.CANCELLED
    assert len(cancelled.entry_gate_results) == 1
    with pytest.raises(harness.HarnessStateError):
        record_fixture_gate(
            run_id=run.run_id,
            caller=codex_agent,
            passed=True,
            command="test",
            summary="cannot resume cancelled",
        )
    replacement = harness.start(contract_id=frozen_id, caller=owner_human)
    assert replacement.run_id != run.run_id


def test_concurrent_starts_create_only_one_active_run(frozen_id: str, owner_human: Human) -> None:
    def start_once(_: int) -> bool:
        try:
            harness.start(contract_id=frozen_id, caller=owner_human)
            return True
        except harness.HarnessStateError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sum(executor.map(start_once, range(2))) == 1
