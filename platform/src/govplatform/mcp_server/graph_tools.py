from __future__ import annotations

from typing import Literal

from mcp.server.mcpserver import MCPServer

from govplatform.graph import proposal_service, query_service, source_service
from govplatform.graph.models import (
    GraphResult,
    Relation,
    RelationKind,
    ReviewSnapshot,
    SourceRevision,
)
from govplatform.graph.query_service import GraphPage
from govplatform.identity.models import Principal


def register_graph_tools(mcp: MCPServer) -> None:
    @mcp.tool(name="graph.source_register")
    async def source_register(
        locator: str,
        caller: Principal,
        content_hash: str | None = None,
        version_label: str | None = None,
        idempotency_key: str | None = None,
        attribution: str | None = None,
        license_note: str | None = None,
    ) -> SourceRevision:
        """登记调用方观察的来源版本；不联网核验，不代表知识已批准。"""
        return source_service.register(
            locator=locator,
            caller=caller,
            content_hash=content_hash,
            version_label=version_label,
            idempotency_key=idempotency_key,
            attribution=attribution,
            license_note=license_note,
        )

    @mcp.tool(name="graph.propose")
    async def propose(
        kind: RelationKind,
        subject_id: str,
        evidence_source_id: str,
        reason: str,
        applicability: str,
        caller: Principal,
        target_knowledge_id: str | None = None,
        target_source_id: str | None = None,
    ) -> Relation:
        """提交待审关系。只有用户批准后才是有效依据，替代关系不自动下线知识。"""
        return proposal_service.propose(
            kind=kind,
            subject_id=subject_id,
            evidence_source_id=evidence_source_id,
            reason=reason,
            applicability=applicability,
            caller=caller,
            target_knowledge_id=target_knowledge_id,
            target_source_id=target_source_id,
        )

    @mcp.tool(name="graph.get")
    async def get(
        key: str,
        kind: Literal["source", "relation"],
        caller: Principal,
    ) -> SourceRevision | ReviewSnapshot | None:
        """查看来源或关系审核快照；待审记录不是生效规则。"""
        return query_service.get(key=key, kind=kind, caller=caller)

    @mcp.tool(name="graph.list")
    async def list_records(
        caller: Principal,
        kind: Literal["source", "relation"] = "relation",
        offset: int = 0,
        limit: int = 20,
    ) -> GraphPage:
        """分页查看图谱目录，包含待审与撤销历史，不能将目录当有效证据。"""
        return query_service.list_records(caller=caller, kind=kind, offset=offset, limit=limit)

    @mcp.tool(name="graph.explain")
    async def explain(
        knowledge_id: str,
        caller: Principal,
        depth: int = 2,
        max_nodes: int = 100,
        max_edges: int = 200,
    ) -> GraphResult:
        """追溯已审核关系，检查 usable/适用范围；truncated 表示证据路径不完整。"""
        return query_service.query(
            key="knowledge:" + knowledge_id,
            caller=caller,
            mode="explain",
            depth=depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )

    @mcp.tool(name="graph.impact")
    async def impact(
        key: str,
        caller: Principal,
        depth: int = 2,
        max_nodes: int = 100,
        max_edges: int = 200,
    ) -> GraphResult:
        """key=source:ID 或 knowledge:ID。查询潜在复检范围，历史路径会标记风险；不是失效判决。"""
        return query_service.query(
            key=key,
            caller=caller,
            mode="impact",
            depth=depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )
