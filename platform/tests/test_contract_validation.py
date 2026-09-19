from __future__ import annotations

import pytest

from govplatform.audit.store import list_audit_events
from govplatform.contract import service as contract_service
from govplatform.contract.models import (
    AcceptanceCriterion,
    ContractStatus,
    VerificationCase,
    VerificationType,
)
from govplatform.contract.service import ContractValidationError
from govplatform.db.connection import get_connection
from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType


def _valid_ac(ac_id: str = "AC-1", test_case_ids: list[str] | None = None) -> AcceptanceCriterion:
    return AcceptanceCriterion(
        ac_id=ac_id,
        precondition="前置条件",
        action="操作步骤",
        input="输入数据",
        expected_result="预期结果",
        verification_type=VerificationType.AUTOMATED_TEST,
        test_case_ids=test_case_ids if test_case_ids is not None else ["TC-1"],
    )


def _create(
    claude_code_agent: Agent,
    *,
    acceptance_criteria: list[AcceptanceCriterion] | None = None,
    test_cases: list[VerificationCase] | None = None,
    knowledge_refs: list[str] | None = None,
) -> str:
    contract = contract_service.create(
        title="待校验的契约",
        goal="目标",
        scope="范围",
        caller=claude_code_agent,
        acceptance_criteria=acceptance_criteria,
        test_cases=test_cases,
        knowledge_refs=knowledge_refs,
    )
    return contract.contract_id


def _assert_rejected_and_still_draft(contract_id: str, owner_human: Human) -> None:
    with pytest.raises(ContractValidationError):
        contract_service.freeze(contract_id=contract_id, caller=owner_human)

    fetched = contract_service.get(contract_id, caller=owner_human)
    assert fetched is not None
    assert fetched.status == ContractStatus.DRAFT

    with get_connection() as conn:
        events = list_audit_events(conn)
    assert any(e.action == "contract.freeze.rejected" for e in events)


def test_freeze_rejects_empty_acceptance_criteria(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _create(claude_code_agent)
    _assert_rejected_and_still_draft(contract_id, owner_human)


def test_freeze_rejects_ac_with_empty_required_field(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    # 对应原方案 §9.2："前置条件、操作、输入、二值化预期结果" 都是硬性
    # 必填字段，不是随便塞个 description 就算数。这里故意不填 expected_result。
    contract_id = _create(
        claude_code_agent,
        acceptance_criteria=[
            AcceptanceCriterion(
                ac_id="AC-1",
                precondition="前置条件",
                action="操作步骤",
                input="输入数据",
                expected_result="",
                verification_type=VerificationType.AUTOMATED_TEST,
                test_case_ids=["TC-1"],
            ),
        ],
        test_cases=[VerificationCase(tc_id="TC-1", description="用例")],
    )
    _assert_rejected_and_still_draft(contract_id, owner_human)


def test_freeze_rejects_ac_with_no_linked_test_case(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _create(
        claude_code_agent,
        acceptance_criteria=[_valid_ac(test_case_ids=[])],
    )
    _assert_rejected_and_still_draft(contract_id, owner_human)


def test_freeze_rejects_ac_referencing_missing_test_case(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _create(
        claude_code_agent,
        acceptance_criteria=[_valid_ac(test_case_ids=["TC-does-not-exist"])],
        test_cases=[VerificationCase(tc_id="TC-1", description="真实存在的用例")],
    )
    _assert_rejected_and_still_draft(contract_id, owner_human)


def test_freeze_rejects_duplicate_ac_id(claude_code_agent: Agent, owner_human: Human) -> None:
    ac = _valid_ac()
    contract_id = _create(
        claude_code_agent,
        acceptance_criteria=[ac, ac],
        test_cases=[VerificationCase(tc_id="TC-1", description="用例")],
    )
    _assert_rejected_and_still_draft(contract_id, owner_human)


def test_freeze_rejects_missing_knowledge_ref(claude_code_agent: Agent, owner_human: Human) -> None:
    contract_id = _create(
        claude_code_agent,
        acceptance_criteria=[_valid_ac()],
        test_cases=[VerificationCase(tc_id="TC-1", description="用例")],
        knowledge_refs=["knowledge-id-that-does-not-exist"],
    )
    _assert_rejected_and_still_draft(contract_id, owner_human)


def test_freeze_rejects_knowledge_ref_that_is_not_active(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    # 提交但没审核通过的知识还是 in_review 状态，不该被契约拿来当依据。
    knowledge = knowledge_service.propose(
        title="还没审核的知识",
        type=KnowledgeType.PROJECT_STANDARD,
        body="正文",
        source="test",
        authority_level=AuthorityLevel.PROJECT,
        caller=claude_code_agent,
    )
    contract_id = _create(
        claude_code_agent,
        acceptance_criteria=[_valid_ac()],
        test_cases=[VerificationCase(tc_id="TC-1", description="用例")],
        knowledge_refs=[knowledge.knowledge_id],
    )
    _assert_rejected_and_still_draft(contract_id, owner_human)


def test_freeze_accepts_existing_knowledge_ref_and_snapshots_it(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    knowledge = knowledge_service.propose(
        title="被契约引用的知识",
        type=KnowledgeType.PROJECT_STANDARD,
        body="正文",
        source="test",
        authority_level=AuthorityLevel.PROJECT,
        caller=claude_code_agent,
    )
    knowledge_service.approve(knowledge_id=knowledge.knowledge_id, caller=owner_human)

    contract_id = _create(
        claude_code_agent,
        acceptance_criteria=[_valid_ac()],
        test_cases=[VerificationCase(tc_id="TC-1", description="用例")],
        knowledge_refs=[knowledge.knowledge_id],
    )

    frozen = contract_service.freeze(contract_id=contract_id, caller=owner_human)
    assert frozen.status == ContractStatus.FROZEN
    assert len(frozen.knowledge_snapshots) == 1
    snapshot = frozen.knowledge_snapshots[0]
    assert snapshot.knowledge_id == knowledge.knowledge_id
    assert snapshot.version == 1
    assert snapshot.content_hash == knowledge.content_hash
