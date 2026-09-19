from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from govplatform.identity.models import Principal


class VerificationType(StrEnum):
    AUTOMATED_TEST = "automated_test"
    MANUAL_EVIDENCE = "manual_evidence"
    BUILD_LOG = "build_log"
    OTHER = "other"


class VerificationCase(BaseModel):
    tc_id: str
    description: str


class AcceptanceCriterion(BaseModel):
    ac_id: str
    # 对应原方案 §9.2 的硬规则："前置条件、操作、输入、二值化预期结果和
    # 验证证据类型"——之前图省事塞进一个 description 里，是漏了结构，
    # 不是新加的严格度。允许草稿期留空字符串，freeze() 时才强制非空。
    precondition: str = ""
    action: str = ""
    input: str = ""
    expected_result: str = ""
    verification_type: VerificationType
    test_case_ids: list[str] = Field(default_factory=list)


class KnowledgeSnapshot(BaseModel):
    """冻结那一刻，被引用知识的版本快照——不是引用本身。

    引用（`Contract.knowledge_refs`）在草稿期可以变；快照只在 freeze()
    成功那一刻由系统自动生成，此后不变，即使被引用的知识后来又被改了、
    归档了，这份快照记录的还是冻结当时的版本和内容指纹。
    """

    knowledge_id: str
    version: int
    content_hash: str


class ContractStatus(StrEnum):
    DRAFT = "draft"
    FROZEN = "frozen"


class Contract(BaseModel):
    contract_id: str
    title: str
    goal: str
    scope: str
    out_of_scope: str | None = None
    author: Principal
    status: ContractStatus = ContractStatus.DRAFT
    version: int = 1
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    test_cases: list[VerificationCase] = Field(default_factory=list)
    knowledge_refs: list[str] = Field(default_factory=list)
    knowledge_snapshots: list[KnowledgeSnapshot] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    frozen_by: str | None = None
    frozen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
