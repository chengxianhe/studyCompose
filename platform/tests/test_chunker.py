from __future__ import annotations

from datetime import UTC, datetime

from govplatform.identity.models import Agent
from govplatform.ingest.chunker import chunk_knowledge
from govplatform.knowledge.models import AuthorityLevel, KnowledgeObject, KnowledgeType


def _knowledge(*, title: str, body: str) -> KnowledgeObject:
    return KnowledgeObject(
        knowledge_id="knowledge-1",
        title=title,
        body=body,
        type=KnowledgeType.PROJECT_STANDARD,
        source="docs/test.md",
        authority_level=AuthorityLevel.PROJECT,
        author=Agent(kind="codex", session_id="test"),
        content_hash="content-v1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_markdown_chunks_keep_parent_and_heading_path() -> None:
    obj = _knowledge(
        title="部署手册",
        body="# 安装\n先下载模型。\n## 验证\n运行离线检查。\n# 运维\n定期核对摘要。",
    )
    chunks = chunk_knowledge(obj)
    assert [chunk.heading_path for chunk in chunks] == [
        ("安装",),
        ("安装", "验证"),
        ("运维",),
    ]
    assert all(chunk.parent_id == obj.knowledge_id for chunk in chunks)
    assert "部署手册 安装 验证" in chunks[1].bm25_field
    assert [chunk.chunk_id for chunk in chunks] == [
        chunk.chunk_id for chunk in chunk_knowledge(obj)
    ]


def test_long_section_is_bounded_and_overlaps() -> None:
    obj = _knowledge(title="长文", body="甲" * 900)
    chunks = chunk_knowledge(obj)
    assert len(chunks) == 2
    assert all(len(chunk.text) <= 700 for chunk in chunks)
    assert chunks[0].text[-80:] == chunks[1].text[:80]
