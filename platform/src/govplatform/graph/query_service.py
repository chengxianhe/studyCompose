from __future__ import annotations

import sqlite3
from collections import deque
from typing import Literal

from pydantic import BaseModel

from govplatform.db.connection import get_connection
from govplatform.graph import store
from govplatform.graph._shared import audit, snapshot, warnings
from govplatform.graph.models import (
    GraphError,
    GraphNode,
    GraphResult,
    Relation,
    RelationView,
    ReviewSnapshot,
    SourceRevision,
)
from govplatform.identity.models import Principal, resolve_principal
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge import store as knowledge_store


class GraphPage(BaseModel):
    items: list[Relation | SourceRevision]
    offset: int
    limit: int
    has_more: bool


def get(
    *,
    key: str,
    kind: Literal["source", "relation"],
    caller: Principal,
) -> SourceRevision | ReviewSnapshot | None:
    principal = resolve_principal(caller)
    with get_connection() as conn:
        if kind == "source":
            result: SourceRevision | ReviewSnapshot | None = store.get_source(conn, key)
        elif kind == "relation":
            obj = store.get_relation(conn, key)
            result = snapshot(conn, obj) if obj else None
        else:
            raise GraphError("unknown record kind")
        audit(conn, principal, "graph.get", key if result else "not_found")
        return result


def list_records(
    *,
    caller: Principal,
    kind: Literal["source", "relation"] = "relation",
    offset: int = 0,
    limit: int = 20,
) -> GraphPage:
    principal = resolve_principal(caller)
    if offset < 0 or offset > 100000 or not 1 <= limit <= 100:
        raise GraphError("offset must be 0..100000; limit must be 1..100")
    if kind not in ("source", "relation"):
        raise GraphError("unknown record kind")
    table, column = (
        ("graph_sources", "source_id") if kind == "source" else ("graph_relations", "relation_id")
    )
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT payload FROM {table} ORDER BY {column} LIMIT ? OFFSET ?", (limit + 1, offset)
        ).fetchall()
        items: list[Relation | SourceRevision] = [
            (
                SourceRevision.model_validate_json(row[0])
                if kind == "source"
                else Relation.model_validate_json(row[0])
            )
            for row in rows[:limit]
        ]
        audit(conn, principal, "graph.list", kind)
    return GraphPage(items=items, offset=offset, limit=limit, has_more=len(rows) > limit)


def _node(conn: sqlite3.Connection, key: str) -> GraphNode:
    category, identity = key.split(":", 1)
    if category == "source":
        source = store.get_source(conn, identity)
        if source:
            return GraphNode(key=key, kind="source", label=source.locator, status="caller_reported")
    elif category == "knowledge":
        obj = knowledge_store.get(conn, identity)
        if obj:
            status = (
                obj.status.value
                if knowledge_service.is_currently_valid(obj)
                else ("not_current:" + obj.status.value)
            )
            return GraphNode(key=key, kind="knowledge", label=obj.title, status=status)
    raise GraphError("unknown graph node")


def query(
    *,
    key: str,
    caller: Principal,
    mode: Literal["explain", "impact"],
    depth: int = 2,
    max_nodes: int = 100,
    max_edges: int = 200,
) -> GraphResult:
    principal = resolve_principal(caller)
    if mode not in ("explain", "impact") or not 1 <= depth <= 3:
        raise GraphError("mode must be explain/impact; depth must be 1..3")
    if not 1 <= max_nodes <= 100 or not 1 <= max_edges <= 200:
        raise GraphError("node/edge budgets must be 1..100 / 1..200")
    result = GraphResult(
        root=key,
        mode=mode,
        meaning=(
            "potential review candidates, including flagged historical paths; "
            "not proof of invalidity"
            if mode == "impact"
            else "reviewed evidence; inspect usable, warnings and applicability"
        ),
    )
    with get_connection() as conn:
        conn.execute("BEGIN")  # One read snapshot for nodes, lifecycle and relation state.
        result.nodes.append(_node(conn, key))
        queue: deque[tuple[str, int, list[str]]] = deque([(key, 0, [])])
        visited = {key}
        emitted: set[str] = set()
        source_ids: set[str] = set()
        while queue:
            current, level, path = queue.popleft()
            remaining = max_edges - len(emitted)
            if level == depth:
                # Replacement metadata is also a relation hop, not a depth-budget exemption.
                adjacent = store.adjacent(conn, current, reverse=mode == "impact", limit=1)
                replacement = (
                    store.replacements(conn, current.split(":", 1)[1], 1)
                    if mode == "impact" and current.startswith("knowledge:")
                    else []
                )
                if adjacent or replacement:
                    result.cutoff_reasons.append("depth_budget")
                continue
            if mode == "impact" and current.startswith("knowledge:"):
                candidates = store.replacements(conn, current.split(":", 1)[1], remaining + 1)
                for candidate in candidates:
                    if len(emitted) >= max_edges:
                        result.cutoff_reasons.append("edge_budget")
                        break
                    emitted.add(candidate.relation_id)
                    issues = warnings(conn, candidate)
                    result.replacement_candidates.append(
                        RelationView(relation=candidate, usable=not issues, warnings=issues)
                    )
                    source_ids.add(candidate.evidence_source_id)
                remaining = max_edges - len(emitted)
            edges = store.adjacent(conn, current, reverse=mode == "impact", limit=remaining + 1)
            for edge in edges:
                if edge.relation_id in emitted:
                    continue
                if len(emitted) >= max_edges:
                    result.cutoff_reasons.append("edge_budget")
                    break
                issues = warnings(conn, edge)
                neighbor = (
                    "knowledge:" + edge.subject.knowledge_id
                    if mode == "impact"
                    else "knowledge:" + edge.target_knowledge.knowledge_id
                    if edge.target_knowledge
                    else "source:" + str(edge.target_source_id)
                )
                if neighbor not in visited and len(visited) >= max_nodes:
                    result.cutoff_reasons.append("node_budget")
                    continue
                emitted.add(edge.relation_id)
                result.relations.append(
                    RelationView(relation=edge, usable=not issues, warnings=issues)
                )
                source_ids.add(edge.evidence_source_id)
                if mode == "explain" and issues:
                    continue
                result.paths.append([*path, edge.relation_id])
                if neighbor not in visited:
                    visited.add(neighbor)
                    result.nodes.append(_node(conn, neighbor))
                    queue.append((neighbor, level + 1, [*path, edge.relation_id]))
        for source_id in sorted(source_ids):
            source = store.get_source(conn, source_id)
            if source:
                result.sources.append(source)
        result.cutoff_reasons = sorted(set(result.cutoff_reasons))
        result.truncated = bool(result.cutoff_reasons)
        audit(conn, principal, "graph." + mode, key)
    return result
