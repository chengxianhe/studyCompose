from __future__ import annotations

import pytest

from govplatform.contract import service as contract_service
from govplatform.contract.models import AcceptanceCriterion, VerificationCase, VerificationType
from govplatform.harness import service as harness_service
from govplatform.harness.models import AcceptanceResult, HarnessStatus
from govplatform.harness.service import HarnessStateError
from govplatform.identity.models import Agent, Human, PrincipalNotAllowedError


def _frozen_contract(claude_code_agent: Agent, owner_human: Human) -> str:
    contract = contract_service.create(
        title="示例功能",
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


def test_start_requires_frozen_contract(claude_code_agent: Agent, owner_human: Human) -> None:
    draft = contract_service.create(
        title="还是草稿", goal="目标", scope="范围", caller=claude_code_agent
    )
    with pytest.raises(HarnessStateError):
        harness_service.start(contract_id=draft.contract_id, caller=owner_human)


def test_start_requires_human_caller(claude_code_agent: Agent, owner_human: Human) -> None:
    contract_id = _frozen_contract(claude_code_agent, owner_human)
    with pytest.raises(PrincipalNotAllowedError):
        harness_service.start(contract_id=contract_id, caller=claude_code_agent)


def test_full_lifecycle_pass_to_delivered(claude_code_agent: Agent, owner_human: Human) -> None:
    contract_id = _frozen_contract(claude_code_agent, owner_human)

    run = harness_service.start(contract_id=contract_id, caller=owner_human)
    assert run.status == HarnessStatus.DEVELOPING

    failed_gate = harness_service.record_entry_gate(
        run_id=run.run_id,
        caller=claude_code_agent,
        passed=False,
        command="pytest",
        summary="1 failed",
    )
    assert failed_gate.status == HarnessStatus.DEVELOPING  # 没过，打回开发

    passed_gate = harness_service.record_entry_gate(
        run_id=run.run_id,
        caller=claude_code_agent,
        passed=True,
        command="pytest",
        summary="all passed",
    )
    assert passed_gate.status == HarnessStatus.ACCEPTING

    accepted = harness_service.record_acceptance(
        run_id=run.run_id,
        caller=claude_code_agent,
        results=[
            AcceptanceResult(ac_id="AC-1", passed=True, evidence_summary="pytest test_ac1 passed")
        ],
    )
    assert accepted.status == HarnessStatus.PASSED

    with pytest.raises(PrincipalNotAllowedError):
        harness_service.deliver(run_id=run.run_id, caller=claude_code_agent)

    delivered = harness_service.deliver(run_id=run.run_id, caller=owner_human)
    assert delivered.status == HarnessStatus.DELIVERED
    assert delivered.delivered_at is not None

    with pytest.raises(HarnessStateError):
        harness_service.deliver(run_id=run.run_id, caller=owner_human)


def test_get_requires_caller_and_is_audited(claude_code_agent: Agent, owner_human: Human) -> None:
    contract_id = _frozen_contract(claude_code_agent, owner_human)
    run = harness_service.start(contract_id=contract_id, caller=owner_human)

    fetched = harness_service.get(run.run_id, caller=owner_human)
    assert fetched is not None
    assert fetched.run_id == run.run_id


def _frozen_contract_with_manual_evidence_ac(claude_code_agent: Agent, owner_human: Human) -> str:
    contract = contract_service.create(
        title="含人工验证项的功能",
        goal="目标",
        scope="范围",
        caller=claude_code_agent,
        acceptance_criteria=[
            AcceptanceCriterion(
                ac_id="AC-1",
                precondition="前置条件",
                action="需要人亲自看的操作",
                input="输入",
                expected_result="预期结果",
                verification_type=VerificationType.MANUAL_EVIDENCE,
                test_case_ids=["TC-1"],
            ),
        ],
        test_cases=[VerificationCase(tc_id="TC-1", description="人工验证")],
    )
    contract_service.freeze(contract_id=contract.contract_id, caller=owner_human)
    return contract.contract_id


def test_agent_cannot_self_pass_manual_evidence_ac(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    """Agent 自己提交 passed=True 判定一条 manual_evidence AC，不能算数——
    这类 AC 设计上就是要留给人亲自确认，不然 Agent 可以绕开"停下来问人"
    这条规则，自己给自己判过。
    """
    contract_id = _frozen_contract_with_manual_evidence_ac(claude_code_agent, owner_human)
    run = harness_service.start(contract_id=contract_id, caller=owner_human)
    harness_service.record_entry_gate(
        run_id=run.run_id, caller=claude_code_agent, passed=True, command="pytest", summary="ok"
    )

    result = harness_service.record_acceptance(
        run_id=run.run_id,
        caller=claude_code_agent,
        results=[
            AcceptanceResult(ac_id="AC-1", passed=True, evidence_summary="我（Agent）觉得过了")
        ],
    )
    # Agent 自称的"通过"不算数，AC-1 仍然是未解决状态——但代码本身没问题
    # （没有真正需要重新开发的失败），不该消耗修复轮次，停在 WAITING_FOR_
    # HUMAN 等人亲自确认或者批豁免，不是 REPAIRING。
    assert result.status == HarnessStatus.WAITING_FOR_HUMAN
    assert result.repair_round == 0


def test_human_can_confirm_manual_evidence_ac(claude_code_agent: Agent, owner_human: Human) -> None:
    contract_id = _frozen_contract_with_manual_evidence_ac(claude_code_agent, owner_human)
    run = harness_service.start(contract_id=contract_id, caller=owner_human)
    harness_service.record_entry_gate(
        run_id=run.run_id, caller=claude_code_agent, passed=True, command="pytest", summary="ok"
    )

    result = harness_service.record_acceptance(
        run_id=run.run_id,
        caller=owner_human,
        results=[
            AcceptanceResult(ac_id="AC-1", passed=True, evidence_summary="我亲自看过了，没问题")
        ],
    )
    assert result.status == HarnessStatus.PASSED


def test_record_acceptance_rejects_unknown_ac_id(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _frozen_contract(claude_code_agent, owner_human)
    run = harness_service.start(contract_id=contract_id, caller=owner_human)
    harness_service.record_entry_gate(
        run_id=run.run_id, caller=claude_code_agent, passed=True, command="pytest", summary="ok"
    )
    with pytest.raises(HarnessStateError):
        harness_service.record_acceptance(
            run_id=run.run_id,
            caller=claude_code_agent,
            results=[
                AcceptanceResult(ac_id="AC-1", passed=True, evidence_summary="ok"),
                AcceptanceResult(ac_id="AC-99", passed=True, evidence_summary="契约里根本没有这条"),
            ],
        )


def test_record_acceptance_rejects_duplicate_ac_id_in_one_batch(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    """同一条 AC 在一批结果里既报失败又报通过，是自相矛盾的证据——之前
    用集合算通过项，只要有一条 passed=True 就会把整条 AC 算作通过，
    忽略了同批里还有一条报 passed=False，悄悄取了对自己有利的那个结论。
    """
    contract_id = _frozen_contract(claude_code_agent, owner_human)
    run = harness_service.start(contract_id=contract_id, caller=owner_human)
    harness_service.record_entry_gate(
        run_id=run.run_id, caller=claude_code_agent, passed=True, command="pytest", summary="ok"
    )
    with pytest.raises(HarnessStateError):
        harness_service.record_acceptance(
            run_id=run.run_id,
            caller=claude_code_agent,
            results=[
                AcceptanceResult(ac_id="AC-1", passed=False, evidence_summary="第一次跑失败了"),
                AcceptanceResult(ac_id="AC-1", passed=True, evidence_summary="重跑了一下过了"),
            ],
        )


def test_human_can_resolve_waiting_for_human_without_rerunning_entry_gate(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    """WAITING_FOR_HUMAN 是"代码没问题，就差人确认"——人推进的时候不用
    重新过一遍入门禁，直接再调用一次 record_acceptance 就行。
    """
    contract_id = _frozen_contract_with_manual_evidence_ac(claude_code_agent, owner_human)
    run = harness_service.start(contract_id=contract_id, caller=owner_human)
    harness_service.record_entry_gate(
        run_id=run.run_id, caller=claude_code_agent, passed=True, command="pytest", summary="ok"
    )
    waiting = harness_service.record_acceptance(
        run_id=run.run_id,
        caller=claude_code_agent,
        results=[
            AcceptanceResult(ac_id="AC-1", passed=True, evidence_summary="我（Agent）觉得过了")
        ],
    )
    assert waiting.status == HarnessStatus.WAITING_FOR_HUMAN

    result = harness_service.record_acceptance(
        run_id=run.run_id,
        caller=owner_human,
        results=[
            AcceptanceResult(ac_id="AC-1", passed=True, evidence_summary="我亲自看过了，没问题")
        ],
    )
    assert result.status == HarnessStatus.PASSED
