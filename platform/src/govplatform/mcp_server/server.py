from __future__ import annotations

from datetime import datetime

from mcp.server.mcpserver import MCPServer

from govplatform.contract import service as contract_service
from govplatform.contract.models import AcceptanceCriterion, Contract, VerificationCase
from govplatform.harness import service as harness_service
from govplatform.harness.models import AcceptanceResult, HarnessRun
from govplatform.identity.models import Principal
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import (
    AuthorityLevel,
    KnowledgeObject,
    KnowledgeStatus,
    KnowledgeType,
)
from govplatform.knowledge.query_service import KnowledgePage, get_knowledge, list_knowledge
from govplatform.knowledge.service import ProposeResponse
from govplatform.mcp_server.graph_tools import register_graph_tools
from govplatform.search import service as search_service
from govplatform.search.service import SearchResponse

mcp = MCPServer("govplatform")
register_graph_tools(mcp)


@mcp.tool(name="knowledge.list")
async def knowledge_list(
    caller: Principal,
    status: KnowledgeStatus | None = KnowledgeStatus.IN_REVIEW,
    offset: int = 0,
    limit: int = 20,
) -> KnowledgePage:
    """浏览候选与有效知识；in_review 内容未经批准，不可作为生效规则。"""
    return list_knowledge(caller=caller, status=status, offset=offset, limit=limit)


@mcp.tool(name="knowledge.get")
async def knowledge_get(knowledge_id: str, caller: Principal) -> KnowledgeObject | None:
    """读取全文和状态；只有 active 且在有效期内的知识才生效。"""
    return get_knowledge(knowledge_id=knowledge_id, caller=caller)


@mcp.tool(name="knowledge.search")
async def knowledge_search(
    query: str,
    caller: Principal,
    knowledge_type: KnowledgeType | None = None,
    limit: int = 10,
    attempt: int = 0,
) -> SearchResponse:
    """检索生效知识。relevance_grade=pass 仅表示候选相关，不代表足以回答。
    answer_assessment=not_assessed 表示平台未评估答案充分性，宿主须按原问题逐项核对：
    所需信息是否齐全，对象/版本/时间/适用范围是否一致，来源是否有效或存在冲突，
    关键结论是否有原文依据。片段不足时用 knowledge.get 读全文并重新核对状态与版本。
    部分有据则只答有据部分并说明缺口；证据不足或冲突未解决时明确说明，不补造网址或数字。
    relevance_grade=retry 时保留原问约束改写 query，递增 attempt，最多重试两轮；
    insufficient 只是内部证据不足，不是任务终点；unavailable 表示判定不可用或降级。
    主动补证：即使 pass 但关键要求未覆盖，也先识别缺口；缺决定性对象才澄清，
    缺可查事实则在授权和预算内使用宿主外查工具，优先一手来源并打开原文核对。
    需要环境证明时在授权内做本地检查；记录实际工具观察，不能把方法说明当执行成功。
    外查后重新核对对象、版本、时间和原文，临时证据不自动入库或覆盖规则。
    内部改写最多两轮；外查共享任务预算，无新增信息时停止重复查找。
    来源冲突、工具不可用、无可靠依据或预算耗尽时，说明已查内容、缺口和停止原因，
    不伪造已联网或已验证。内部充分时直接回答，不机械外查，不外发私有原文或凭据。
    此工具不调用云端 LLM，也不替宿主执行语义核对。
    """
    return search_service.search(
        query=query, caller=caller, knowledge_type=knowledge_type, limit=limit, attempt=attempt
    )


@mcp.tool(name="knowledge.propose")
async def knowledge_propose(
    title: str,
    type: KnowledgeType,
    body: str,
    source: str,
    authority_level: AuthorityLevel,
    caller: Principal,
    tags: list[str] | None = None,
    effective_at: datetime | None = None,
    expire_at: datetime | None = None,
) -> ProposeResponse:
    obj = knowledge_service.propose(
        title=title,
        type=type,
        body=body,
        source=source,
        authority_level=authority_level,
        caller=caller,
        tags=tags,
        effective_at=effective_at,
        expire_at=expire_at,
    )
    return ProposeResponse(knowledge_id=obj.knowledge_id, status=obj.status, version=obj.version)


@mcp.tool(name="contract.create")
async def contract_create(
    title: str,
    goal: str,
    scope: str,
    caller: Principal,
    out_of_scope: str | None = None,
    acceptance_criteria: list[AcceptanceCriterion] | None = None,
    test_cases: list[VerificationCase] | None = None,
    knowledge_refs: list[str] | None = None,
    risks: list[str] | None = None,
    open_questions: list[str] | None = None,
) -> Contract:
    return contract_service.create(
        title=title,
        goal=goal,
        scope=scope,
        caller=caller,
        out_of_scope=out_of_scope,
        acceptance_criteria=acceptance_criteria,
        test_cases=test_cases,
        knowledge_refs=knowledge_refs,
        risks=risks,
        open_questions=open_questions,
    )


@mcp.tool(name="contract.update")
async def contract_update(
    contract_id: str,
    caller: Principal,
    expected_version: int,
    title: str | None = None,
    goal: str | None = None,
    scope: str | None = None,
    out_of_scope: str | None = None,
    acceptance_criteria: list[AcceptanceCriterion] | None = None,
    test_cases: list[VerificationCase] | None = None,
    knowledge_refs: list[str] | None = None,
    risks: list[str] | None = None,
    open_questions: list[str] | None = None,
) -> Contract:
    return contract_service.update(
        contract_id=contract_id,
        caller=caller,
        expected_version=expected_version,
        title=title,
        goal=goal,
        scope=scope,
        out_of_scope=out_of_scope,
        acceptance_criteria=acceptance_criteria,
        test_cases=test_cases,
        knowledge_refs=knowledge_refs,
        risks=risks,
        open_questions=open_questions,
    )


@mcp.tool(name="contract.get")
async def contract_get(contract_id: str, caller: Principal) -> Contract | None:
    return contract_service.get(contract_id, caller=caller)


@mcp.tool(name="harness.record_entry_gate")
async def harness_record_entry_gate(
    run_id: str, caller: Principal, passed: bool, command: str, summary: str
) -> HarnessRun:
    """需先 delivery prepare；summary 必须为真实 VerificationEvidence JSON，不接受自报通过。"""
    return harness_service.record_entry_gate(
        run_id=run_id, caller=caller, passed=passed, command=command, summary=summary
    )


@mcp.tool(name="harness.record_acceptance")
async def harness_record_acceptance(
    run_id: str, caller: Principal, results: list[AcceptanceResult]
) -> HarnessRun:
    return harness_service.record_acceptance(run_id=run_id, caller=caller, results=results)


@mcp.tool(name="harness.get")
async def harness_get(run_id: str, caller: Principal) -> HarnessRun | None:
    return harness_service.get(run_id, caller=caller)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
