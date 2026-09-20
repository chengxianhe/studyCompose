from __future__ import annotations

from datetime import datetime

from mcp.server.mcpserver import MCPServer

from govplatform.contract import service as contract_service
from govplatform.contract.models import AcceptanceCriterion, Contract, VerificationCase
from govplatform.harness import service as harness_service
from govplatform.harness.models import AcceptanceResult, HarnessRun
from govplatform.identity.models import Principal
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeType
from govplatform.knowledge.service import ProposeResponse
from govplatform.search import service as search_service
from govplatform.search.service import SearchResponse

mcp = MCPServer("govplatform")


@mcp.tool(name="knowledge.search")
async def knowledge_search(
    query: str,
    caller: Principal,
    knowledge_type: KnowledgeType | None = None,
    limit: int = 10,
) -> SearchResponse:
    return search_service.search(
        query=query, caller=caller, knowledge_type=knowledge_type, limit=limit
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
