from __future__ import annotations

from mcp.server.mcpserver import MCPServer

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
) -> ProposeResponse:
    obj = knowledge_service.propose(
        title=title,
        type=type,
        body=body,
        source=source,
        authority_level=authority_level,
        caller=caller,
        tags=tags,
    )
    return ProposeResponse(knowledge_id=obj.knowledge_id, status=obj.status, version=obj.version)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
