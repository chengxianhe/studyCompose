from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from govplatform import embedding
from govplatform.config import db_path
from govplatform.db.connection import get_connection
from govplatform.evaluation import fixtures, runner
from govplatform.evaluation.metrics import aggregate, ranking_metrics
from govplatform.evaluation.models import Case, CaseResult, Dataset
from govplatform.ingest.__main__ import _active_objects
from govplatform.knowledge import service
from govplatform.search.service import SearchResponse


def dataset() -> Dataset:
    return Dataset.model_validate_json(
        (Path(__file__).resolve().parents[1] / "evals/retrieval-v1.json").read_bytes()
    )


def test_dataset_contract_rejects_bad_labels_and_duplicate_ids() -> None:
    source = dataset()
    assert len(source.cases) == 16 and source.label_status == "draft"
    for change in (
        {"documents": [*source.documents, source.documents[0]]},
        {"cases": [*source.cases, source.cases[0]]},
        {"cases": [source.cases[0].model_copy(update={"relevant": ["missing"]})]},
        {"cases": [source.cases[0].model_copy(update={"relevant": ["travel-expired"]})]},
        {"cases": [source.cases[0].model_copy(update={"relevant": []})]},
    ):
        with pytest.raises(ValidationError):
            Dataset.model_validate({**source.model_dump(), **change})


def test_metrics_document_ranking_and_failure_coverage() -> None:
    assert ranking_metrics(["a", "a", "b"], ["b", "c"]) == (0.5, 0.5)
    failed = CaseResult(
        id="failed", group="unanswerable", query="none", expected=[], elapsed_ms=1, status="error"
    )
    result = aggregate([failed])
    assert result["unanswerable_correct"] is None
    assert result["graded_unanswerable_cases"] == 0
    assert result["failed_or_degraded_cases"] == 1
    with pytest.raises(ValueError):
        ranking_metrics([], [])


def test_isolation_restores_environment_after_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    production = tmp_path / "production.db"
    production.write_bytes(b"do not modify")
    monkeypatch.setenv("GOVPLAT_DB_PATH", str(production))
    monkeypatch.setenv("GOVPLAT_ES_INDEX_ALIAS", "production_alias")
    original = {
        key: os.environ.get(key)
        for key in ("GOVPLAT_DB_PATH", "GOVPLAT_ES_URL", "GOVPLAT_ES_INDEX_ALIAS", "HF_HUB_OFFLINE")
    }

    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("synthetic seed failure")

    monkeypatch.setattr(service, "propose", fail)
    with pytest.raises(RuntimeError):
        with fixtures.corpus(dataset(), "sqlite", None):
            pass
    assert {key: os.environ.get(key) for key in original} == original
    assert production.read_bytes() == b"do not modify"
    with pytest.raises(ValueError):
        with fixtures.corpus(dataset(), "elasticsearch", "https://remote.example.test"):
            pass
    assert {key: os.environ.get(key) for key in original} == original
    with pytest.raises(ValueError):
        with fixtures.corpus(dataset(), "elasticsearch", None):
            pass
    assert {key: os.environ.get(key) for key in original} == original


def test_refuses_existing_target_and_never_seeds_production(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "synthetic.sqlite"
    target.write_bytes(b"existing")

    @contextmanager
    def existing_directory(*_args: object, **_kwargs: object) -> Iterator[str]:
        yield str(tmp_path)

    monkeypatch.setattr(tempfile, "TemporaryDirectory", existing_directory)
    with pytest.raises(ValueError):
        with fixtures.corpus(dataset(), "sqlite", None):
            pass
    assert target.read_bytes() == b"existing"


def test_synthetic_lifecycle_and_production_db_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    original = db_path()
    with get_connection() as conn:
        before = conn.execute("SELECT COUNT(*) FROM knowledge_objects").fetchone()[0]

    def offline(_: str) -> bytes:
        raise RuntimeError("no model needed for isolation test")

    monkeypatch.setattr(embedding, "embed", offline)
    with fixtures.corpus(dataset(), "sqlite", None) as mapping:
        assert db_path() != original and len(mapping) == 11
        objects = _active_objects()
        assert len(objects) == 9
        assert {mapping[obj.knowledge_id] for obj in objects}.isdisjoint(
            {"travel-expired", "payment-deprecated"}
        )
    assert db_path() == original
    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM knowledge_objects").fetchone()[0] == before


def test_fallback_or_exception_is_not_correct_abstention(monkeypatch: pytest.MonkeyPatch) -> None:
    case = Case(id="absent", group="unanswerable", query="none", relevant=[], rationale="none")
    monkeypatch.setattr(
        runner,
        "search",
        lambda **_: SearchResponse(
            query="none",
            results=[],
            retrieval_backend="sqlite_fallback",
            retrieval_mode="hybrid",
            relevance_grade="unavailable",
        ),
    )
    result = runner.evaluate_case(case, "elasticsearch", {}, set())
    assert result.status == "degraded" and result.no_answer_correct is None
    result = runner.evaluate_case(case, "sqlite", {}, set())
    assert result.status == "ok" and result.no_answer_correct is None

    def error(**_kwargs: object) -> SearchResponse:
        raise RuntimeError("backend failed")

    monkeypatch.setattr(runner, "search", error)
    result = runner.evaluate_case(case, "elasticsearch", {}, set())
    assert result.status == "error" and result.no_answer_correct is None


def test_cleanup_cannot_delete_production_index() -> None:
    client = MagicMock()
    with pytest.raises(ValueError):
        runner._remove_index(
            client, "govplatform_knowledge_chunks_v1_live", "govplatform_knowledge_chunks"
        )
    client.indices.delete.assert_not_called()
