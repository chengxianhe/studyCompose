from __future__ import annotations

from govplatform.contract import service as contract_service
from govplatform.contract.models import AcceptanceCriterion, VerificationCase, VerificationType
from govplatform.identity.models import Agent
from govplatform.mcp_server.server import contract_create, contract_get, contract_update


async def test_mcp_create_update_get_round_trip(claude_code_agent: Agent) -> None:
    created = await contract_create(
        title="MCP 起草的契约",
        goal="目标",
        scope="范围",
        caller=claude_code_agent,
    )
    assert created.status.value == "draft"

    updated = await contract_update(
        contract_id=created.contract_id,
        caller=claude_code_agent,
        expected_version=created.version,
        acceptance_criteria=[
            AcceptanceCriterion(
                ac_id="AC-1",
                precondition="前置条件",
                action="通过 MCP 补的操作",
                input="输入",
                expected_result="预期结果",
                verification_type=VerificationType.AUTOMATED_TEST,
                test_case_ids=["TC-1"],
            ),
        ],
        test_cases=[VerificationCase(tc_id="TC-1", description="用例")],
    )
    assert len(updated.acceptance_criteria) == 1

    fetched = await contract_get(created.contract_id, caller=claude_code_agent)
    assert fetched is not None
    assert fetched.contract_id == created.contract_id
    assert len(fetched.acceptance_criteria) == 1

    # freeze 不是 MCP 工具，这里直接调 service 层确认 contract_get 拿到的
    # 是最新数据（跟 knowledge 那套一样，写操作走 MCP，freeze 只走 HTTP）。
    assert contract_service.get(created.contract_id, caller=claude_code_agent) is not None
