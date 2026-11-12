from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from govplatform.evaluation.evidence_trace import CompletionCases, EvidenceTrace


def trace() -> dict[str, Any]:
    return {
        "case_id": "external_completion",
        "mode": "fixture_replay",
        "assessed_by": "synthetic-test-host",
        "original_query": "Where is the SQLite backup documentation?",
        "subject": "SQLite",
        "internal_grade": "pass",
        "observations": [
            {
                "id": "internal",
                "action": "internal_search",
                "tool": "knowledge.search",
                "status": "success",
                "result": "Related backup material without a URL.",
                "observed_at": "2026-11-12T00:00:00Z",
            },
            {
                "id": "search",
                "action": "external_search",
                "tool": "fixture-search",
                "status": "success",
                "result": "Found official documentation.",
                "gap": "Missing official URL",
                "observed_at": "2026-11-12T00:00:01Z",
            },
            {
                "id": "read",
                "action": "read_source",
                "tool": "fixture-open",
                "status": "success",
                "result": "SQLite Online Backup API provides a database snapshot.",
                "locator": "https://www.sqlite.org/backup.html",
                "observed_at": "2026-11-12T00:00:02Z",
            },
        ],
        "evidence": [
            {
                "id": "e1",
                "observation_id": "read",
                "locator": "https://www.sqlite.org/backup.html",
                "quote": "Online Backup API",
                "kind": "external",
                "subject": "SQLite",
            }
        ],
        "requirements": [
            {
                "id": "url",
                "need": "Official URL",
                "assessment": "covered",
                "evidence_ids": ["e1"],
                "reason": "Host read the official source.",
            }
        ],
        "max_external_searches": 1,
        "outcome": "answered",
        "answer": "The official documentation is https://www.sqlite.org/backup.html.",
        "stop_reason": "Required URL located and opened.",
    }


def test_pass_does_not_end_a_task_with_missing_url() -> None:
    value = EvidenceTrace.model_validate(trace())
    assert value.internal_grade == "pass"
    assert value.observations[1].action == "external_search"
    assert value.answer_assessment == "host_reported"


@pytest.mark.parametrize(
    "fault",
    [
        "unknown_observation", "failed_read", "search_summary", "quote", "locator",
        "unknown_reference", "duplicate_evidence", "duplicate_observation", "duplicate_requirement",
        "missing_reference", "duplicate_reference", "budget", "gap", "subject", "version",
        "local_claim", "missing_internal", "naive_time", "not_covered",
    ],
)
def test_reject_invalid_execution_and_citation_claims(fault: str) -> None:
    data = trace()
    evidence = data["evidence"][0]
    requirement = data["requirements"][0]
    observation = data["observations"][-1]
    if fault == "unknown_observation":
        evidence["observation_id"] = "unknown"
    elif fault == "failed_read":
        observation["status"] = "error"
    elif fault == "search_summary":
        observation["action"] = "external_search"
        observation["gap"] = "URL"
        data["max_external_searches"] = 2
    elif fault == "quote":
        evidence["quote"] = "text never observed"
    elif fault == "locator":
        evidence["locator"] = "https://wrong.example/"
    elif fault == "unknown_reference":
        requirement["evidence_ids"] = ["unknown"]
    elif fault == "duplicate_evidence":
        data["evidence"].append(deepcopy(evidence))
    elif fault == "duplicate_observation":
        data["observations"].append(deepcopy(observation))
    elif fault == "duplicate_requirement":
        data["requirements"].append(deepcopy(requirement))
    elif fault == "missing_reference":
        requirement["evidence_ids"] = []
    elif fault == "duplicate_reference":
        requirement["evidence_ids"] = ["e1", "e1"]
    elif fault == "budget":
        data["max_external_searches"] = 0
    elif fault == "gap":
        data["observations"][1]["gap"] = None
    elif fault == "subject":
        evidence["subject"] = "Another database"
    elif fault == "version":
        data["required_version"] = "3.34.0"
        evidence["applicable_version"] = "3.35.0"
    elif fault == "local_claim":
        evidence["kind"] = "local"
    elif fault == "missing_internal":
        data["observations"].pop(0)
    elif fault == "naive_time":
        observation["observed_at"] = "2026-11-12T00:00:02"
    elif fault == "not_covered":
        requirement["assessment"] = "partial"
    with pytest.raises(ValidationError):
        EvidenceTrace.model_validate(data)


def test_clarification_and_unavailable_are_not_fabricated_success() -> None:
    data = trace()
    data["evidence"] = []
    data["requirements"][0].update(assessment="missing", evidence_ids=[])
    data["outcome"] = "needs_clarification"
    with pytest.raises(ValidationError, match="actually presented"):
        EvidenceTrace.model_validate(data)
    data["observations"] = [data["observations"][0], {
        "id": "ask", "action": "clarify", "tool": "host-message", "status": "success",
        "result": "Which organization?", "observed_at": "2026-11-12T00:00:02Z",
    }]
    assert EvidenceTrace.model_validate(data).outcome == "needs_clarification"
    data["observations"][-1].update(action="external_search", status="unavailable", gap="URL")
    data["outcome"] = "blocked"
    assert EvidenceTrace.model_validate(data).outcome == "blocked"


def test_partial_requires_actual_support_and_a_gap() -> None:
    data = trace()
    data["outcome"] = "partial"
    with pytest.raises(ValidationError, match="unresolved gap"):
        EvidenceTrace.model_validate(data)
    data["requirements"].append({
        "id": "login", "need": "Login steps", "assessment": "missing",
        "evidence_ids": [], "reason": "Not documented.",
    })
    assert EvidenceTrace.model_validate(data).outcome == "partial"


def test_cases_are_draft_and_cover_success_and_failure() -> None:
    path = Path(__file__).resolve().parents[1] / "evals/evidence-completion-v1.json"
    cases = CompletionCases.model_validate_json(path.read_bytes())
    assert cases.label_status == "draft" and len(cases.cases) == 6
    bad = cases.model_dump()
    bad["cases"].append(bad["cases"][0])
    with pytest.raises(ValidationError, match="duplicate case"):
        CompletionCases.model_validate(bad)


def test_release_document_can_support_a_comparison_with_an_older_target() -> None:
    data = trace()
    data["required_version"] = "3.34.0"
    data["evidence"][0].update(source_version="3.35.0", applicable_version="3.34.0")
    data["requirements"][0]["reason"] = "Host compared introduction with the older target."
    result = EvidenceTrace.model_validate(data)
    assert result.evidence[0].source_version != result.required_version
