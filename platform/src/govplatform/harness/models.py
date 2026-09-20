from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HarnessStatus(StrEnum):
    DEVELOPING = "developing"
    ACCEPTING = "accepting"
    REPAIRING = "repairing"
    PASSED = "passed"
    DELIVERED = "delivered"
    ESCALATED = "escalated"


class GateResult(BaseModel):
    passed: bool
    command: str
    summary: str
    recorded_at: datetime


class AcceptanceResult(BaseModel):
    ac_id: str
    passed: bool
    evidence_summary: str
    # 调用方不用自己操心这个时间戳——默认取"这个对象被构造出来的那一刻"，
    # 跟批次里其他结果、跟 record_acceptance() 调用本身的时间基本同步，
    # 不需要精确到毫秒对齐。
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # 这条结果是第几轮验收产生的——由 record_acceptance() 内部按当时的
    # repair_round 盖章，调用方传什么都会被覆盖。加这个字段是因为
    # acceptance_results 现在是跨轮次累积的完整历史（不再是"只留最新一
    # 轮"），需要能分清楚每条证据属于哪一轮，不然多轮之后没法回溯"当时
    # 到底提交了什么证据"。
    round_number: int = 0


class RepairRound(BaseModel):
    round_number: int
    failure_summary: str
    started_at: datetime


class HarnessRun(BaseModel):
    run_id: str
    contract_id: str
    status: HarnessStatus = HarnessStatus.DEVELOPING
    repair_round: int = 0
    entry_gate_results: list[GateResult] = Field(default_factory=list)
    acceptance_results: list[AcceptanceResult] = Field(default_factory=list)
    repair_rounds: list[RepairRound] = Field(default_factory=list)
    escalation_reason: str | None = None
    started_by: str
    created_at: datetime
    updated_at: datetime
    delivered_at: datetime | None = None
