from __future__ import annotations

from govplatform.contract import service as contract_service
from govplatform.contract.models import AcceptanceCriterion, VerificationCase, VerificationType
from govplatform.harness import service as harness_service
from govplatform.harness.models import AcceptanceResult, HarnessStatus
from govplatform.identity.models import Agent, Human


def _frozen_contract(claude_code_agent: Agent, owner_human: Human) -> str:
    contract = contract_service.create(
        title="容易失败的功能",
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
            ),
        ],
        test_cases=[VerificationCase(tc_id="TC-1", description="用例")],
    )
    contract_service.freeze(contract_id=contract.contract_id, caller=owner_human)
    return contract.contract_id


def _pass_entry_gate(run_id: str, caller: Agent) -> None:
    harness_service.record_entry_gate(
        run_id=run_id, caller=caller, passed=True, command="pytest", summary="ok"
    )


def _fail_acceptance(run_id: str, caller: Agent) -> None:
    harness_service.record_acceptance(
        run_id=run_id,
        caller=caller,
        results=[AcceptanceResult(ac_id="AC-1", passed=False, evidence_summary="pytest failed")],
    )


def test_repeated_failure_escalates_after_exhausting_three_repair_rounds(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _frozen_contract(claude_code_agent, owner_human)
    run = harness_service.start(contract_id=contract_id, caller=owner_human)

    # 第 1-3 次验收失败，依次进入修复第 1、2、3 轮——"最多三轮修复"指的是
    # 修复循环本身最多绕三圈，不是"第三次失败就升级"。
    for expected_round in (1, 2, 3):
        _pass_entry_gate(run.run_id, claude_code_agent)
        _fail_acceptance(run.run_id, claude_code_agent)
        current = harness_service.get(run.run_id, caller=owner_human)
        assert current is not None
        assert current.status == HarnessStatus.REPAIRING
        assert current.repair_round == expected_round

    # 第三轮修复之后再验收，第 4 次仍然失败——三轮修复的机会已经用完，
    # 这次直接升级，不会开出第四轮。
    _pass_entry_gate(run.run_id, claude_code_agent)
    _fail_acceptance(run.run_id, claude_code_agent)
    escalated = harness_service.get(run.run_id, caller=owner_human)
    assert escalated is not None
    assert escalated.status == HarnessStatus.ESCALATED
    assert escalated.repair_round == 3  # 停在第三轮，没有第四轮
    assert escalated.escalation_reason is not None
    assert "AC-1" in escalated.escalation_reason
    assert len(escalated.repair_rounds) == 3


def test_success_after_one_repair_round_reaches_passed(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _frozen_contract(claude_code_agent, owner_human)
    run = harness_service.start(contract_id=contract_id, caller=owner_human)

    _pass_entry_gate(run.run_id, claude_code_agent)
    _fail_acceptance(run.run_id, claude_code_agent)
    after_first_failure = harness_service.get(run.run_id, caller=owner_human)
    assert after_first_failure is not None
    assert after_first_failure.status == HarnessStatus.REPAIRING
    assert after_first_failure.repair_round == 1

    _pass_entry_gate(run.run_id, claude_code_agent)
    passed = harness_service.record_acceptance(
        run_id=run.run_id,
        caller=claude_code_agent,
        results=[AcceptanceResult(ac_id="AC-1", passed=True, evidence_summary="fixed, now passes")],
    )
    assert passed.status == HarnessStatus.PASSED
    # 走到第几轮才过的，如实记下来，不会假装是一次就过的。
    assert passed.repair_round == 1
    assert len(passed.repair_rounds) == 1

    # 第一轮失败的证据不能被第二轮覆盖掉——acceptance_results 是跨轮次
    # 累积的完整历史，两条都应该还在，分别标着自己产生时的轮次号。
    assert len(passed.acceptance_results) == 2
    assert [r.passed for r in passed.acceptance_results] == [False, True]
    assert [r.round_number for r in passed.acceptance_results] == [0, 1]
