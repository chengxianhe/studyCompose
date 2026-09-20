from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from govplatform.contract import service as contract_service
from govplatform.contract.models import AcceptanceCriterion, VerificationCase, VerificationType
from govplatform.contract.service import (
    ContractStateError,
    ContractValidationError,
    WaiverNotAllowedError,
)
from govplatform.harness import service as harness_service
from govplatform.harness.models import AcceptanceResult, HarnessStatus
from govplatform.identity.models import Agent, Human, PrincipalNotAllowedError

_NOW = datetime.now(UTC)


def _create_contract(
    claude_code_agent: Agent,
    *,
    touches_production: bool = False,
    risks: list[str] | None = None,
) -> str:
    contract = contract_service.create(
        title="需要豁免的功能",
        goal="目标",
        scope="范围",
        caller=claude_code_agent,
        acceptance_criteria=[
            AcceptanceCriterion(
                ac_id="AC-1",
                precondition="前置条件",
                action="操作",
                input="输入",
                expected_result="预期结果",
                verification_type=VerificationType.AUTOMATED_TEST,
                test_case_ids=["TC-1"],
                touches_production_or_irreversible=touches_production,
            ),
        ],
        test_cases=[VerificationCase(tc_id="TC-1", description="用例")],
        risks=risks,
    )
    return contract.contract_id


def test_valid_waiver_lets_acceptance_pass_despite_failure(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _create_contract(claude_code_agent)
    contract_service.freeze(contract_id=contract_id, caller=owner_human)

    contract_service.request_waiver(
        contract_id=contract_id,
        ac_id="AC-1",
        caller=owner_human,
        reason="CI 环境没法模拟这个场景，人工验证过了",
        risk="小概率边界情况没覆盖到",
        expires_at=_NOW + timedelta(days=7),
    )

    run = harness_service.start(contract_id=contract_id, caller=owner_human)
    harness_service.record_entry_gate(
        run_id=run.run_id, caller=claude_code_agent, passed=True, command="pytest", summary="ok"
    )
    accepted = harness_service.record_acceptance(
        run_id=run.run_id,
        caller=claude_code_agent,
        results=[AcceptanceResult(ac_id="AC-1", passed=False, evidence_summary="没法自动验证")],
    )
    assert accepted.status == HarnessStatus.PASSED


def test_expired_waiver_does_not_cover_the_ac(claude_code_agent: Agent, owner_human: Human) -> None:
    contract_id = _create_contract(claude_code_agent)
    contract_service.freeze(contract_id=contract_id, caller=owner_human)

    contract_service.request_waiver(
        contract_id=contract_id,
        ac_id="AC-1",
        caller=owner_human,
        reason="临时豁免",
        risk="风险",
        expires_at=_NOW - timedelta(days=1),  # 已经过期
    )

    run = harness_service.start(contract_id=contract_id, caller=owner_human)
    harness_service.record_entry_gate(
        run_id=run.run_id, caller=claude_code_agent, passed=True, command="pytest", summary="ok"
    )
    accepted = harness_service.record_acceptance(
        run_id=run.run_id,
        caller=claude_code_agent,
        results=[AcceptanceResult(ac_id="AC-1", passed=False, evidence_summary="仍未通过")],
    )
    # 过期豁免不生效，fail closed——回到"未解决"，进入修复轮次，不是 PASSED。
    assert accepted.status == HarnessStatus.REPAIRING


def test_waiver_requires_frozen_contract(claude_code_agent: Agent, owner_human: Human) -> None:
    """草稿期的 AC 内容还能被 update() 改掉，豁免针对的必须是冻结后不会
    再变的内容——之前的实现没查契约状态，草稿期就能批豁免。
    """
    contract_id = _create_contract(claude_code_agent)
    with pytest.raises(ContractStateError):
        contract_service.request_waiver(
            contract_id=contract_id,
            ac_id="AC-1",
            caller=owner_human,
            reason="契约还没冻结就想批豁免",
            risk="风险",
            expires_at=_NOW + timedelta(days=7),
        )


def test_waiver_requires_human(claude_code_agent: Agent) -> None:
    contract_id = _create_contract(claude_code_agent)
    with pytest.raises(PrincipalNotAllowedError):
        contract_service.request_waiver(
            contract_id=contract_id,
            ac_id="AC-1",
            caller=claude_code_agent,
            reason="AI 不该能自己批准豁免",
            risk="风险",
            expires_at=_NOW + timedelta(days=7),
        )


def test_touches_production_ac_cannot_be_waived(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _create_contract(
        claude_code_agent, touches_production=True, risks=["有回滚方案：xxx"]
    )
    contract_service.freeze(contract_id=contract_id, caller=owner_human)
    with pytest.raises(WaiverNotAllowedError):
        contract_service.request_waiver(
            contract_id=contract_id,
            ac_id="AC-1",
            caller=owner_human,
            reason="想豁免涉及生产数据的检查",
            risk="风险",
            expires_at=_NOW + timedelta(days=7),
        )


def test_freeze_rejects_missing_rollback_plan_when_touching_production(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _create_contract(claude_code_agent, touches_production=True, risks=None)
    with pytest.raises(ContractValidationError):
        contract_service.freeze(contract_id=contract_id, caller=owner_human)


def test_freeze_accepts_when_touching_production_with_rollback_plan(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _create_contract(
        claude_code_agent, touches_production=True, risks=["有回滚方案：关闭 feature flag"]
    )
    frozen = contract_service.freeze(contract_id=contract_id, caller=owner_human)
    assert frozen.status.value == "frozen"
