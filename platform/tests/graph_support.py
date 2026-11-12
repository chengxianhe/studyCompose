"""Synthetic graph fixtures only; never approves records in the live database."""

from dataclasses import dataclass

import pytest

from govplatform import embedding
from govplatform.graph import proposal_service, query_service, review_service, source_service
from govplatform.graph.models import Relation, ReviewSnapshot, SourceRevision
from govplatform.identity.models import Agent, Human
from govplatform.knowledge import service
from govplatform.knowledge.models import AuthorityLevel, KnowledgeObject, KnowledgeType
from govplatform.review.views import fingerprint


@dataclass
class GraphCase:
    old: KnowledgeObject
    new: KnowledgeObject
    dependent: KnowledgeObject
    source: SourceRevision


def seed(
    agent: Agent, human: Human, monkeypatch: pytest.MonkeyPatch, domain: str = "api"
) -> GraphCase:
    def offline(_: str) -> bytes:
        raise RuntimeError("synthetic test: no embedding required")

    monkeypatch.setattr(embedding, "embed", offline)
    objects = []
    titles = (
        ("API A 旧指引", "API B 新指引", "SDK migration checklist")
        if domain == "api"
        else ("旧版报销流程", "Revised reimbursement process", "报销材料提交")
    )
    for title in titles:
        obj = service.propose(
            title=title,
            body=title + "。适用条件详见来源。",
            source="synthetic://guide",
            type=KnowledgeType.REFERENCE,
            authority_level=AuthorityLevel.REFERENCE,
            caller=agent,
        )
        service.approve(knowledge_id=obj.knowledge_id, caller=human)
        objects.append(obj)
    source = source_service.register(
        locator="synthetic://guide", content_hash="a" * 64, version_label="2026", caller=agent
    )
    return GraphCase(objects[0], objects[1], objects[2], source)


def link(case: GraphCase, agent: Agent, kind: str = "derived_from") -> Relation:
    if kind == "derived_from":
        return proposal_service.propose(
            kind="derived_from",
            subject_id=case.old.knowledge_id,
            target_source_id=case.source.source_id,
            evidence_source_id=case.source.source_id,
            reason="旧指引引用此版本 / derived from this revision",
            applicability="旧版流程",
            caller=agent,
        )
    return proposal_service.propose(
        kind="depends_on",
        subject_id=case.dependent.knowledge_id,
        target_knowledge_id=case.old.knowledge_id,
        evidence_source_id=case.source.source_id,
        reason="材料清单依赖旧指引",
        applicability="旧版流程",
        caller=agent,
    )


def snapshot_for(obj: Relation, caller: Agent | Human) -> str:
    result = query_service.get(key=obj.relation_id, kind="relation", caller=caller)
    assert isinstance(result, ReviewSnapshot)
    return fingerprint(result)


def approve(obj: Relation, human: Human) -> Relation:
    return review_service.review(
        relation_id=obj.relation_id,
        caller=human,
        action="approve",
        expected_snapshot=snapshot_for(obj, human),
    )
