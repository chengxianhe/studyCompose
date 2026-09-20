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
    # 涉及生产数据或者不可逆操作的验收标准，标 True。用途：①这类 AC 不
    # 允许申请豁免（哪怕修复三次都通不过，也不能绕过，必须真做对）；
    # ②契约冻结时如果有 AC 标了这个，risks 字段不能为空（必须写清楚
    # 回滚方案）。两条限制都是从 Anthropic 自己公开的工程实践（关键动作
    # 永远人工终审）和国内大厂"变更三板斧"（可回滚）调研来的，不是拍脑袋
    # 加的字段。
    touches_production_or_irreversible: bool = False


class KnowledgeSnapshot(BaseModel):
    """冻结那一刻，被引用知识的版本快照——不是引用本身。

    引用（`Contract.knowledge_refs`）在草稿期可以变；快照只在 freeze()
    成功那一刻由系统自动生成，此后不变，即使被引用的知识后来又被改了、
    归档了，这份快照记录的还是冻结当时的版本和内容指纹。
    """

    knowledge_id: str
    version: int
    content_hash: str


class Waiver(BaseModel):
    """契约里某条验收标准的例外——不是"这条不用管了"，是"承担了这个
    风险，有到期时间，到期自动失效"。设计依据见
    `docs/ai-engineering-governed-delivery-platform-baseline.md` §7.3
    （调研 SOC2/DevSecOps 领域关于豁免机制的共识）：独立对象、精确关联
    到哪个契约的哪条 AC（不能笼统豁免整份契约）、只有 Human 能创建、
    必填理由/风险/到期时间、不允许永久豁免。
    """

    waiver_id: str
    contract_id: str
    ac_id: str
    reason: str
    risk: str
    approved_by: str
    created_at: datetime
    expires_at: datetime


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
