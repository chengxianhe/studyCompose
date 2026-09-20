from __future__ import annotations

import pytest

from govplatform.contract import service as contract_service
from govplatform.contract import store as contract_store
from govplatform.contract.models import (
    AcceptanceCriterion,
    ContractStatus,
    VerificationCase,
    VerificationType,
)
from govplatform.contract.service import ContractConflictError, ContractStateError
from govplatform.db.connection import get_connection
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
        contract_id=contract_id,
        caller=claude_code_agent,
        expected_version=1,
        title="收藏文章功能（改标题）",
    )
    assert updated.title == "收藏文章功能（改标题）"
    assert updated.version == 2

    contract_service.freeze(contract_id=contract_id, caller=owner_human)

    with pytest.raises(ContractStateError):
        contract_service.update(
            contract_id=contract_id,
            caller=claude_code_agent,
            expected_version=2,
            title="冻结后还想改",
        )


def test_update_rejects_stale_expected_version(
    claude_code_agent: Agent, owner_human: Human
) -> None:
    contract_id = _minimal_valid_contract(claude_code_agent)

    # Codex 先改了一次，版本从 1 变成 2。
    contract_service.update(
        contract_id=contract_id,
        caller=claude_code_agent,
        expected_version=1,
        title="Codex 改的标题",
    )

    # Claude Code 手上还是版本 1 的旧数据，这时候提交会被拒绝，而不是
    # 悄悄覆盖 Codex 刚写的东西。
    with pytest.raises(ContractConflictError):
        contract_service.update(
            contract_id=contract_id,
            caller=claude_code_agent,
            expected_version=1,
            title="基于旧数据改的标题",
        )

    # 拒绝之后契约还是 Codex 写的那个版本，没有被部分覆盖。
    fetched = contract_service.get(contract_id, caller=owner_human)
    assert fetched is not None
    assert fetched.title == "Codex 改的标题"
    assert fetched.version == 2


def test_store_update_is_atomic_on_version_mismatch(claude_code_agent: Agent) -> None:
    """contract_service.update() 的版本检查真正生效的地方是
    contract_store.update() 里那条 `WHERE ... AND version = ?`——直接在
    store 层验证：expected_version 对不上，SQL 写入本身就不会生效
    （rowcount==0，返回 False），不是靠上层 Python 代码里"先读一次、判断
    通过再写"这个有时间窗口的检查来保证。这样即使两个调用几乎同时读到
    了同一个旧版本、都通过了 Python 层的检查，后写入的那个在真正执行
    UPDATE 时也会因为版本已经被前一个改掉而失败，不会静默覆盖。
    """
    contract_id = _minimal_valid_contract(claude_code_agent)
    contract = contract_service.get_without_audit(contract_id)
    assert contract is not None
    assert contract.version == 1

    # 模拟两个调用几乎同时读到了同一份版本 1 的数据——"先写的那个"把版本
    # 从 1 改成 2 并成功。
    first_write = contract.model_copy(update={"title": "先写的那个", "version": 2})
    with get_connection() as conn:
        succeeded = contract_store.update(conn, first_write, expected_version=1)
        assert succeeded

    # "后写的那个"手上还是基于版本 1 读到的旧数据（它并不知道上面那次已经
    # 写过了），拿着 expected_version=1 去写，此时数据库里实际版本已经是
    # 2，应该原子性地失败，不能静默覆盖掉第一次写入。
    with get_connection() as conn:
        second_write = contract.model_copy(update={"title": "后写的那个", "version": 2})
        succeeded = contract_store.update(conn, second_write, expected_version=1)
        assert not succeeded

    final = contract_service.get_without_audit(contract_id)
    assert final is not None
    assert final.title == "先写的那个"
    assert final.version == 2


def test_freeze_records_who_and_when(claude_code_agent: Agent, owner_human: Human) -> None:
    contract_id = _minimal_valid_contract(claude_code_agent)

    frozen = contract_service.freeze(contract_id=contract_id, caller=owner_human)

    assert frozen.status == ContractStatus.FROZEN
    assert frozen.frozen_by == owner_human.id
    assert frozen.frozen_at is not None

    fetched = contract_service.get(contract_id, caller=owner_human)
    assert fetched is not None
    assert fetched.status == ContractStatus.FROZEN
