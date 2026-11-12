from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from govplatform.identity.models import Principal

RelationKind = Literal["derived_from", "depends_on", "supersedes"]
RelationStatus = Literal["in_review", "active", "revoked"]


class GraphError(ValueError):
    """Invalid graph input or a stale governance request."""


class SourceRevision(BaseModel):
    source_id: str
    locator: str
    version_label: str | None = None
    content_hash: str | None = None
    attribution: str | None = None
    license_note: str | None = None
    author: Principal
    observed_at: datetime
    verification: Literal["caller_reported"] = "caller_reported"


class KnowledgeRef(BaseModel):
    knowledge_id: str
    version: int
    content_hash: str


class Relation(BaseModel):
    relation_id: str
    kind: RelationKind
    subject: KnowledgeRef
    target_knowledge: KnowledgeRef | None = None
    target_source_id: str | None = None
    evidence_source_id: str
    reason: str
    applicability: str
    author: Principal
    status: RelationStatus = "in_review"
    created_at: datetime
    updated_at: datetime
    approved_by: str | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None


class ReviewSnapshot(BaseModel):
    relation: Relation
    sources: list[SourceRevision]
    knowledge_states: list[dict[str, str | int | bool | None]]


class RelationView(BaseModel):
    relation: Relation
    usable: bool
    warnings: list[str]


class GraphNode(BaseModel):
    key: str
    kind: Literal["knowledge", "source"]
    label: str
    status: str


class GraphResult(BaseModel):
    root: str
    mode: Literal["explain", "impact"]
    nodes: list[GraphNode] = Field(default_factory=list)
    relations: list[RelationView] = Field(default_factory=list)
    replacement_candidates: list[RelationView] = Field(default_factory=list)
    paths: list[list[str]] = Field(default_factory=list)
    sources: list[SourceRevision] = Field(default_factory=list)
    truncated: bool = False
    cutoff_reasons: list[str] = Field(default_factory=list)
    meaning: str
