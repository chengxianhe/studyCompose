from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Backend = Literal["sqlite", "elasticsearch"]


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    state: Literal["active", "expired", "deprecated"] = "active"


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    group: Literal["chinese", "english", "updates", "unanswerable"]
    query: str = Field(min_length=1, max_length=1000)
    relevant: list[str]
    rationale: str = Field(min_length=1)


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    label_status: Literal["draft", "human_reviewed"]
    documents: list[Document] = Field(min_length=1, max_length=100)
    cases: list[Case] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_references(self) -> Dataset:
        docs = {doc.id: doc for doc in self.documents}
        if len(docs) != len(self.documents) or len({case.id for case in self.cases}) != len(
            self.cases
        ):
            raise ValueError("duplicate document/case ID")
        for case in self.cases:
            if len(set(case.relevant)) != len(case.relevant):
                raise ValueError("duplicate relevance label")
            if (case.group == "unanswerable") != (not case.relevant):
                raise ValueError("only unanswerable cases may have empty relevance labels")
            if any(key not in docs or docs[key].state != "active" for key in case.relevant):
                raise ValueError("relevance labels must refer to active documents")
        return self


class CaseResult(BaseModel):
    id: str
    group: str
    query: str
    expected: list[str]
    ranked: list[str] = Field(default_factory=list)
    status: Literal["ok", "degraded", "error"]
    backend: str | None = None
    mode: str | None = None
    grade: str | None = None
    elapsed_ms: float
    recall_at_5: float | None = None
    mrr_at_10: float | None = None
    no_answer_correct: bool | None = None
    lifecycle_violations: list[str] = Field(default_factory=list)
    error_type: str | None = None


class BackendReport(BaseModel):
    requested_backend: Backend
    setup_ms: float
    warmup_ms: float
    results: list[CaseResult]
    metrics: dict[str, float | int | None]
    group_metrics: dict[str, dict[str, float | int | None]]
    error_type: str | None = None


class EvaluationReport(BaseModel):
    dataset_version: str
    dataset_sha256: str
    label_status: str
    code_sha256: str
    configuration: dict[str, str | int | bool]
    backends: list[BackendReport]
    limitations: list[str]
