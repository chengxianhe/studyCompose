"""Validate host-reported evidence traces, not semantic truth or tool authenticity.

No network access, model calls or knowledge writes. Quotes are checked against
recorded tool observations; a fabricated record can still pass this local format.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=32000)]
Key = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")]


class TraceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Observation(TraceRecord):
    id: Key
    action: Literal["internal_search", "read_source", "external_search", "clarify", "local_check"]
    tool: Text
    status: Literal["success", "error", "unavailable"]
    result: Text
    observed_at: AwareDatetime
    # Exact source location for reads; external_search summaries aren't source reads.
    locator: Text | None = None
    gap: Text | None = None


class Evidence(TraceRecord):
    id: Key
    observation_id: Key
    locator: Text
    quote: Text
    kind: Literal["internal", "external", "local"]
    subject: Text
    source_version: Text | None = None
    # Host-assessed applicability may differ from the document's release version.
    applicable_version: Text | None = None


class Requirement(TraceRecord):
    id: Key
    need: Text
    assessment: Literal["covered", "partial", "missing", "conflict"]
    evidence_ids: list[Key] = Field(default_factory=list, max_length=40)
    # Semantic assessment is explicitly made by the host, not this validator.
    reason: Text


class EvidenceTrace(TraceRecord):
    case_id: Key
    mode: Literal["host_observed", "fixture_replay"]
    assessed_by: Text
    original_query: Text
    subject: Text | None = None
    required_version: Text | None = None
    internal_grade: Literal["pass", "retry", "insufficient", "unavailable"]
    observations: list[Observation] = Field(min_length=1, max_length=80)
    evidence: list[Evidence] = Field(default_factory=list, max_length=80)
    requirements: list[Requirement] = Field(min_length=1, max_length=40)
    max_external_searches: int = Field(ge=0, le=20)
    outcome: Literal[
        "answered", "partial", "needs_clarification", "unresolved", "blocked", "budget_exhausted"
    ]
    answer: Text
    stop_reason: Text
    answer_assessment: Literal["host_reported"] = "host_reported"

    @model_validator(mode="after")
    def check_links_and_outcome(self) -> Self:
        observations = {item.id: item for item in self.observations}
        evidence = {item.id: item for item in self.evidence}
        if len(observations) != len(self.observations) or len(evidence) != len(self.evidence):
            raise ValueError("duplicate observation or evidence ID")
        if len({item.id for item in self.requirements}) != len(self.requirements):
            raise ValueError("duplicate requirement ID")
        if not any(item.action == "internal_search" for item in self.observations):
            raise ValueError("record the internal search, including failures")
        external = [item for item in self.observations if item.action == "external_search"]
        if len(external) > self.max_external_searches:
            raise ValueError("external search budget exceeded")
        if any(not item.gap for item in external):
            raise ValueError("external searches must identify the information gap")
        for item in self.evidence:
            observation = observations.get(item.observation_id)
            if observation is None or observation.status != "success":
                raise ValueError("evidence requires a successful recorded observation")
            if observation.action not in ("read_source", "local_check"):
                raise ValueError("search summaries or clarification are not source reads")
            if observation.locator != item.locator or item.quote not in observation.result:
                raise ValueError("quote and locator must match the recorded source")
            if (item.kind == "local") != (observation.action == "local_check"):
                raise ValueError("local execution evidence must come from a local check")
        for requirement in self.requirements:
            refs = requirement.evidence_ids
            if len(set(refs)) != len(refs) or any(ref not in evidence for ref in refs):
                raise ValueError("duplicate or unknown evidence reference")
            if requirement.assessment in ("covered", "partial", "conflict") and not refs:
                raise ValueError("supported or conflicting claims need evidence")
            if requirement.assessment == "covered":
                if self.subject and any(evidence[ref].subject != self.subject for ref in refs):
                    raise ValueError("covered requirement uses another subject")
                if self.required_version and any(
                    evidence[ref].applicable_version != self.required_version for ref in refs
                ):
                    raise ValueError("covered requirement uses an inapplicable version")
        if self.outcome == "answered" and any(
            item.assessment != "covered" for item in self.requirements
        ):
            raise ValueError("answered requires every requirement to be covered")
        if self.outcome == "partial" and not (
            any(item.assessment in ("covered", "partial") for item in self.requirements)
            and any(item.assessment != "covered" for item in self.requirements)
        ):
            raise ValueError("partial requires both support and an unresolved gap")
        if self.outcome == "needs_clarification" and not any(
            item.action == "clarify" and item.status == "success" for item in self.observations
        ):
            raise ValueError("record the question actually presented to the user")
        return self


class CompletionCase(TraceRecord):
    id: Key
    query: Text
    context: Text
    expected_behavior: Text
    forbidden_behavior: Text


class CompletionCases(TraceRecord):
    version: Literal["evidence-completion-v1"]
    label_status: Literal["draft", "human_reviewed"]
    cases: list[CompletionCase] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def check_ids(self) -> Self:
        if len({item.id for item in self.cases}) != len(self.cases):
            raise ValueError("duplicate case ID")
        return self
