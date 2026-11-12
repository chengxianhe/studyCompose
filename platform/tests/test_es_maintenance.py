from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from elasticsearch import helpers

from govplatform.identity.models import Agent
from govplatform.ingest import es_index
from govplatform.ingest.es_maintenance import discard_unpublished_target, prune_orphan_indices
from govplatform.ingest.health import diagnose
from govplatform.knowledge.models import AuthorityLevel, KnowledgeObject, KnowledgeType


def _object() -> KnowledgeObject:
    return KnowledgeObject(
        knowledge_id="knowledge-1",
        title="本地检索",
        body="知识由离线索引同步。",
        type=KnowledgeType.PROJECT_STANDARD,
        source="docs/search.md",
        authority_level=AuthorityLevel.PROJECT,
        author=Agent(kind="codex", session_id="test"),
        content_hash="hash-1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_prune_only_old_unaliased_indices() -> None:
    now = datetime(2026, 11, 10, tzinfo=UTC)
    old = int((now - timedelta(hours=2)).timestamp() * 1000)
    recent = int((now - timedelta(minutes=5)).timestamp() * 1000)
    client = MagicMock()
    client.indices.get.return_value = {
        "knowledge_v1_current": {
            "aliases": {"knowledge": {}},
            "settings": {"index": {"creation_date": str(old)}},
        },
        "knowledge_v1_old": {"aliases": {}, "settings": {"index": {"creation_date": str(old)}}},
        "knowledge_v1_recent": {
            "aliases": {},
            "settings": {"index": {"creation_date": str(recent)}},
        },
        "knowledge_v1_shared": {
            "aliases": {"another": {}},
            "settings": {"index": {"creation_date": str(old)}},
        },
    }

    removed = prune_orphan_indices(
        client, alias="knowledge", protected={"knowledge_v1_current"}, now=now
    )

    assert removed == ["knowledge_v1_old"]
    client.indices.get.assert_called_once_with(index="knowledge_v*")
    client.indices.delete.assert_called_once_with(index="knowledge_v1_old")


def test_failed_build_discards_unpublished_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOVPLAT_ES_INDEX_ALIAS", "knowledge")
    obj = _object()
    target = es_index.expected_index([obj])
    client = MagicMock()
    client.indices.get_alias.return_value = {"knowledge_v1_old": {}}
    client.indices.exists.return_value = False
    client.indices.get.return_value = {target: {"aliases": {}}}

    def fail_bulk(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("bulk failed")

    monkeypatch.setattr(helpers, "bulk", fail_bulk)
    with pytest.raises(RuntimeError, match="bulk failed"):
        es_index.sync_index(client, [obj])

    client.indices.delete.assert_called_once_with(index=target)
    client.indices.update_aliases.assert_not_called()


def test_failed_build_never_discards_published_target() -> None:
    client = MagicMock()
    client.indices.get.return_value = {"knowledge_v1_current": {"aliases": {"knowledge": {}}}}

    assert discard_unpublished_target(client, target="knowledge_v1_current") is False
    client.indices.delete.assert_not_called()


def test_successful_switch_removes_old_index_atomically(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOVPLAT_ES_INDEX_ALIAS", "knowledge")
    target = es_index.expected_index([])
    client = MagicMock()
    client.indices.get_alias.return_value = {"knowledge_v1_old": {}}
    client.indices.exists.return_value = False
    monkeypatch.setattr(es_index, "prune_orphan_indices", lambda *_args, **_kwargs: [])

    assert es_index.sync_index(client, []) == target
    client.indices.update_aliases.assert_called_once_with(
        actions=[
            {"remove_index": {"index": "knowledge_v1_old"}},
            {"add": {"index": target, "alias": "knowledge"}},
        ]
    )
    client.indices.delete.assert_not_called()


def test_doctor_reports_unavailable_es_without_changing_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from govplatform.ingest import health

    monkeypatch.setattr(health, "_models_ready", lambda: (True, True))
    client = MagicMock()
    client.cluster.health.side_effect = OSError("connection refused")

    report = diagnose(client, [])

    assert report["ready"] is False
    assert report["es_reachable"] is False
    assert report["embedding_ready"] is True
    client.indices.get_alias.assert_not_called()


def test_doctor_reports_ready_for_current_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    from govplatform.ingest import health

    monkeypatch.setenv("GOVPLAT_ES_INDEX_ALIAS", "knowledge")
    monkeypatch.setattr(health, "_models_ready", lambda: (True, True))
    client = MagicMock()
    client.cluster.health.return_value = {"status": "yellow"}
    client.indices.get_alias.return_value = {es_index.expected_index([]): {}}

    report = diagnose(client, [])

    assert report["ready"] is True
    assert report["es_reachable"] is True
    assert report["index_ready"] is True
