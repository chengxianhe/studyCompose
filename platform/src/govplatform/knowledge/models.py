from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from govplatform.identity.models import Principal


class KnowledgeType(StrEnum):
    ORGANIZATION_STANDARD = "organization_standard"
    PROJECT_STANDARD = "project_standard"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    PROJECT_FACT = "project_fact"
    EXPERIENCE = "experience"
    TASK_DECISION = "task_decision"
    REFERENCE = "reference"


class AuthorityLevel(StrEnum):
    ORGANIZATION = "organization"
    PROJECT = "project"
    TASK = "task"
    REFERENCE = "reference"


class KnowledgeStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class KnowledgeObject(BaseModel):
    knowledge_id: str
    title: str
    type: KnowledgeType
    body: str
    source: str
    author: Principal
    owner: str | None = None
    authority_level: AuthorityLevel
    status: KnowledgeStatus = KnowledgeStatus.DRAFT
    version: int = 1
    effective_at: datetime | None = None
    expire_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    content_hash: str
    created_at: datetime
    updated_at: datetime
