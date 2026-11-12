from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest
from graph_support import approve, link, seed
from mcp import Client, StdioServerParameters

from govplatform.backup import create_backup, inspect_database, restore_backup
from govplatform.config import db_path
from govplatform.db.connection import get_connection
from govplatform.graph.models import GraphResult, Relation, SourceRevision
from govplatform.identity.models import Agent, Human


def test_graph_backup_and_legacy_upgrade(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch)
    approve(link(case, codex_agent), owner_human)
    snapshot = create_backup(db_path(), tmp_path / "graph-backup")
    restored = tmp_path / "graph-restored.db"
    counts = restore_backup(snapshot, restored)
    assert counts["graph_sources"] == 1 and counts["graph_relations"] == 1
    with sqlite3.connect(restored) as conn:
        conn.execute("DROP TABLE graph_relations")
        conn.execute("DROP TABLE graph_sources")
    legacy = create_backup(restored, tmp_path / "legacy-backup")
    upgraded = tmp_path / "upgraded.db"
    assert "graph_sources" not in restore_backup(legacy, upgraded)
    monkeypatch.setenv("GOVPLAT_DB_PATH", str(upgraded))
    for _ in range(2):
        with get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM knowledge_objects").fetchone()[0] == 3
            assert conn.execute("SELECT COUNT(*) FROM graph_sources").fetchone()[0] == 0
    assert inspect_database(upgraded)["graph_relations"] == 0


@pytest.mark.parametrize("domain", ["api", "process"])
async def test_graph_over_real_stdio_mcp(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
    domain: str,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch, domain)
    origin = approve(link(case, codex_agent), owner_human)
    approve(link(case, codex_agent, "depends_on"), owner_human)
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "govplatform.mcp_server.server"],
        env=dict(os.environ),
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    async with Client(server, read_timeout_seconds=30) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        assert {"graph.propose", "graph.source_register", "graph.explain", "graph.impact"} <= names
        assert not {"graph.approve", "graph.revoke"} & names
        args = {"knowledge_id": case.old.knowledge_id, "caller": codex_agent.model_dump()}
        response = await client.call_tool("graph.explain", args)
        assert not response.is_error
        result = GraphResult.model_validate(response.structured_content)
        assert result.paths == [[origin.relation_id]]
        assert result.sources[0].content_hash == case.source.content_hash
        invalid = await client.call_tool("graph.explain", {**args, "depth": 4})
        assert invalid.is_error
        response = await client.call_tool(
            "graph.impact",
            {"key": "source:" + case.source.source_id, "caller": codex_agent.model_dump()},
        )
        assert not response.is_error
        assert len(GraphResult.model_validate(response.structured_content).paths) == 2
        response = await client.call_tool(
            "graph.source_register",
            {
                "locator": "synthetic://next",
                "idempotency_key": domain,
                "caller": codex_agent.model_dump(),
            },
        )
        assert not response.is_error
        source = SourceRevision.model_validate(response.structured_content)
        response = await client.call_tool(
            "graph.propose",
            {
                "kind": "supersedes",
                "subject_id": case.new.knowledge_id,
                "target_knowledge_id": case.old.knowledge_id,
                "evidence_source_id": source.source_id,
                "reason": "New guide replaces previous guidance",
                "applicability": "New process only",
                "caller": codex_agent.model_dump(),
            },
        )
        assert not response.is_error
        relation = Relation.model_validate(response.structured_content)
        assert relation.status == "in_review"
        for tool, params in (
            ("graph.list", {"limit": 1}),
            ("graph.get", {"kind": "source", "key": source.source_id}),
            ("graph.get", {"kind": "relation", "key": relation.relation_id}),
        ):
            response = await client.call_tool(tool, {**params, "caller": codex_agent.model_dump()})
            assert not response.is_error
