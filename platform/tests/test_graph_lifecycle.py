from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from graph_support import approve, link, seed, snapshot_for

from govplatform.db.connection import get_connection
from govplatform.graph import proposal_service, query_service, review_service, source_service
from govplatform.graph.models import GraphError, GraphResult, Relation
from govplatform.identity.models import Agent, Human, PrincipalNotAllowedError
from govplatform.knowledge import service as knowledge


def test_sources_dedup_unknown_digest_and_sensitive_inputs(codex_agent: Agent) -> None:
    source = source_service.register(
        locator="synthetic://same", content_hash="f" * 64, caller=codex_agent
    )
    assert (
        source_service.register(
            locator="synthetic://same", content_hash="f" * 64, caller=codex_agent
        )
        == source
    )
    unknown = source_service.register(
        locator="synthetic://same", idempotency_key="attempt1", caller=codex_agent
    )
    assert unknown.source_id != source.source_id
    assert (
        source_service.register(
            locator="synthetic://same", idempotency_key="attempt1", caller=codex_agent
        )
        == unknown
    )
    with pytest.raises(GraphError, match="different metadata"):
        source_service.register(
            locator="synthetic://same",
            idempotency_key="attempt1",
            version_label="v2",
            caller=codex_agent,
        )
    for args in (
        {"locator": "synthetic://same"},
        {"locator": "x", "content_hash": "bad"},
        {"locator": "https://user:secret@example.test", "idempotency_key": "x"},
        {"locator": "https://example.test?token=secret", "idempotency_key": "x"},
    ):
        with pytest.raises(GraphError):
            source_service.register(caller=codex_agent, **args)
    with get_connection() as conn:
        events = " ".join(row[0] for row in conn.execute("SELECT request_json FROM audit_events"))
    assert "secret" not in events


def test_pending_approval_revocation_and_unchanged_search(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch)
    relation = link(case, codex_agent)

    def impact() -> GraphResult:
        return query_service.query(
            key="source:" + case.source.source_id, mode="impact", caller=codex_agent
        )

    assert not impact().relations
    with pytest.raises(PrincipalNotAllowedError):
        review_service.review(
            relation_id=relation.relation_id,
            caller=codex_agent,
            action="approve",
            expected_snapshot=snapshot_for(relation, codex_agent),
        )
    approve(relation, owner_human)
    assert len(impact().relations) == 1
    review_service.review(
        relation_id=relation.relation_id,
        caller=owner_human,
        action="revoke",
        reason="引用错误",
        expected_snapshot=snapshot_for(relation, owner_human),
    )
    result = impact()
    assert len(result.relations) == 1 and not result.relations[0].usable
    assert result.relations[0].warnings == ["relation_revoked"]
    current = knowledge.get(case.old.knowledge_id)
    assert current is not None and current.status.value == "active"


def test_stale_snapshot_and_expired_endpoint_cannot_be_approved(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch)
    relation = link(case, codex_agent)
    expected = snapshot_for(relation, owner_human)
    with get_connection() as conn:
        conn.execute(
            "UPDATE knowledge_objects SET expire_at=? WHERE knowledge_id=?",
            ((datetime.now(UTC) - timedelta(seconds=1)).isoformat(), case.old.knowledge_id),
        )
    for stamp in (expected, snapshot_for(relation, owner_human)):
        with pytest.raises(GraphError):
            review_service.review(
                relation_id=relation.relation_id,
                caller=owner_human,
                action="approve",
                expected_snapshot=stamp,
            )


def test_constraints_and_supersedes_cycle(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch)
    relation = link(case, codex_agent)
    with pytest.raises(GraphError, match="already"):
        link(case, codex_agent)

    def replace(subject: str, target: str) -> Relation:
        return proposal_service.propose(
            kind="supersedes",
            subject_id=subject,
            target_knowledge_id=target,
            evidence_source_id=case.source.source_id,
            reason="API B 替代 API A",
            applicability="新项目",
            caller=codex_agent,
        )

    replacement = replace(case.new.knowledge_id, case.old.knowledge_id)
    approve(replacement, owner_human)
    impact = query_service.query(
        key="knowledge:" + case.old.knowledge_id, mode="impact", caller=codex_agent
    )
    assert impact.replacement_candidates[0].relation.relation_id == replacement.relation_id
    assert impact.paths == []  # A replacement is not a dependency.
    for target in (case.new.knowledge_id, "unknown"):
        with pytest.raises(GraphError):
            replace(case.new.knowledge_id, target)
    inverse = replace(case.old.knowledge_id, case.new.knowledge_id)
    with pytest.raises(GraphError, match="cycle"):
        approve(inverse, owner_human)
    assert relation.status == "in_review"


def test_parallel_approval_only_commits_once(
    codex_agent: Agent,
    owner_human: Human,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = seed(codex_agent, owner_human, monkeypatch)
    relation = link(case, codex_agent)
    expected = snapshot_for(relation, owner_human)

    def attempt(_: int) -> bool:
        try:
            review_service.review(
                relation_id=relation.relation_id,
                caller=owner_human,
                expected_snapshot=expected,
                action="approve",
            )
            return True
        except GraphError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(attempt, range(2))) == 1
    with get_connection() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM audit_events WHERE action='graph.approve'"
            ).fetchone()[0]
            == 1
        )
