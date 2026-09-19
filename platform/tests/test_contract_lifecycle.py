from __future__ import annotations

import pytest

from govplatform.contract import service as contract_service
from govplatform.contract.models import (
    AcceptanceCriterion,
    ContractStatus,
    VerificationCase,
    VerificationType,
)
from govplatform.contract.service import ContractStateError
from govplatform.identity.models import Agent, Human


def _minimal_valid_contract(claude_code_agent: Agent) -> str:
    contract = contract_service.create(
        title="收藏文章功能",
        goal="用户可以收藏/取消收藏文章，重启应用后收藏状态保留",
        scope="文章详情页的收藏按钮、收藏列表页、本地持久化",
        caller=claude_code_agent,
        acceptance_criteria=[
            AcceptanceCriterion(
                ac_id="AC-1",
                precondition="用户已打开一篇文章详情页",
                action="点击收藏按钮",
                input="无",
                expected_result="文章出现在收藏列表里",
                verification_type=VerificationType.AUTOMATED_TEST,
                test_case_ids=["TC-1"],
            ),
        ],
        test_cases=[VerificationCase(tc_id="TC-1", description="点击收藏 -> 断言列表包含该文章")],
    )
    return contract.contract_id


def test_create_starts_as_draft(claude_code_agent: Agent) -> None:
    contract = contract_service.create(
        title="草稿契约",
        goal="随便一个目标",
        scope="随便一个范围",
        caller=claude_code_agent,
    )
    assert contract.status == ContractStatus.DRAFT
    assert contract.version == 1
    assert contract.frozen_by is None


def test_update_only_allowed_while_draft(claude_code_agent: Agent, owner_human: Human) -> None:
    contract_id = _minimal_valid_contract(claude_code_agent)

    updated = contract_service.update(
        contract_id=contract_id, caller=claude_code_agent, title="收藏文章功能（改标题）"
    )
    assert updated.title == "收藏文章功能（改标题）"

    contract_service.freeze(contract_id=contract_id, caller=owner_human)

    with pytest.raises(ContractStateError):
        contract_service.update(
            contract_id=contract_id, caller=claude_code_agent, title="冻结后还想改"
        )


def test_freeze_records_who_and_when(claude_code_agent: Agent, owner_human: Human) -> None:
    contract_id = _minimal_valid_contract(claude_code_agent)

    frozen = contract_service.freeze(contract_id=contract_id, caller=owner_human)

    assert frozen.status == ContractStatus.FROZEN
    assert frozen.frozen_by == owner_human.id
    assert frozen.frozen_at is not None

    fetched = contract_service.get(contract_id, caller=owner_human)
    assert fetched is not None
    assert fetched.status == ContractStatus.FROZEN
