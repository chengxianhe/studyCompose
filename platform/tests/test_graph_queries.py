from __future__ import annotations

import pytest
from graph_support import approve, link, seed

from govplatform.db.connection import get_connection
from govplatform.graph import proposal_service, query_service
from govplatform.graph.models import GraphError
from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service as knowledge


def test_explain_and_impact_keep_correct_direction_and_historical_risk(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch)
    origin = approve(link(case, codex_agent), owner_human)
    dependency = approve(link(case, codex_agent, "depends_on"), owner_human)
    forward = query_service.query(
        key="knowledge:" + case.dependent.knowledge_id, mode="explain", caller=codex_agent
    )
    assert forward.paths == [[dependency.relation_id], [dependency.relation_id, origin.relation_id]]
    assert not forward.truncated
    assert forward.sources == [case.source]
    reverse = query_service.query(
        key="source:" + case.source.source_id, mode="impact", caller=codex_agent
    )
    assert reverse.paths == [[origin.relation_id], [origin.relation_id, dependency.relation_id]]
    assert {node.key for node in reverse.nodes} == {
        "source:" + case.source.source_id,
        "knowledge:" + case.old.knowledge_id,
        "knowledge:" + case.dependent.knowledge_id,
    }
    knowledge.deprecate(knowledge_id=case.old.knowledge_id, caller=owner_human, reason="新版取代")
    historical = query_service.query(
        key="source:" + case.source.source_id, mode="impact", caller=codex_agent
    )
    assert historical.paths == reverse.paths
    assert all(not edge.usable for edge in historical.relations)
    forward = query_service.query(
        key="knowledge:" + case.dependent.knowledge_id, mode="explain", caller=codex_agent
    )
    assert forward.paths == []


def test_budgets_cycles_and_digest_changes(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch)
    approve(link(case, codex_agent), owner_human)
    approve(link(case, codex_agent, "depends_on"), owner_human)
    inverse = proposal_service.propose(
        kind="depends_on",
        subject_id=case.old.knowledge_id,
        target_knowledge_id=case.dependent.knowledge_id,
        evidence_source_id=case.source.source_id,
        reason="双向流程约束",
        applicability="测试流程",
        caller=codex_agent,
    )
    approve(inverse, owner_human)
    for options, cutoff in (
        ({"max_nodes": 1}, "node_budget"),
        ({"max_edges": 1}, "edge_budget"),
        ({"depth": 1}, "depth_budget"),
    ):
        result = query_service.query(
            key="knowledge:" + case.old.knowledge_id, mode="explain", caller=codex_agent, **options
        )
        assert result.truncated and cutoff in result.cutoff_reasons
        assert len(result.nodes) <= options.get("max_nodes", 100)
        assert len(result.relations) <= options.get("max_edges", 200)
    finite = query_service.query(
        key="knowledge:" + case.old.knowledge_id, mode="impact", depth=3, caller=codex_agent
    )
    assert len(finite.nodes) == 2 and len(finite.relations) == 2
    with get_connection() as conn:
        conn.execute(
            "UPDATE knowledge_objects SET content_hash=? WHERE knowledge_id=?",
            ("b" * 64, case.old.knowledge_id),
        )
    changed = query_service.query(
        key="knowledge:" + case.old.knowledge_id, mode="explain", caller=codex_agent
    )
    assert changed.paths == []
    assert all(
        any("endpoint_changed" in warning for warning in edge.warnings)
        for edge in changed.relations
    )


def test_invalid_query_and_listing_parameters(codex_agent: Agent) -> None:
    with pytest.raises(GraphError):
        query_service.query(key="unknown", mode="impact", caller=codex_agent, depth=4)
    with pytest.raises(GraphError):
        query_service.query(key="knowledge:missing", mode="impact", caller=codex_agent)
    for offset, limit in ((-1, 10), (0, 101)):
        with pytest.raises(GraphError):
            query_service.list_records(caller=codex_agent, offset=offset, limit=limit)


def test_depth_budget_also_limits_replacement_candidates(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch)
    approve(link(case, codex_agent), owner_human)
    replacement = proposal_service.propose(
        kind="supersedes",
        subject_id=case.new.knowledge_id,
        target_knowledge_id=case.old.knowledge_id,
        evidence_source_id=case.source.source_id,
        reason="新流程替代旧流程",
        applicability="新版项目",
        caller=codex_agent,
    )
    approve(replacement, owner_human)
    shallow = query_service.query(
        key="source:" + case.source.source_id, mode="impact", depth=1, caller=codex_agent
    )
    assert shallow.replacement_candidates == []
    assert shallow.truncated and "depth_budget" in shallow.cutoff_reasons
    deeper = query_service.query(
        key="source:" + case.source.source_id, mode="impact", depth=2, caller=codex_agent
    )
    assert [view.relation.relation_id for view in deeper.replacement_candidates] == [
        replacement.relation_id
    ]
