from __future__ import annotations

import hashlib
from pathlib import Path
from time import perf_counter

from elasticsearch import Elasticsearch

from govplatform import model_cache, rerank_model
from govplatform.evaluation.fixtures import EVALUATOR, corpus
from govplatform.evaluation.metrics import aggregate, ranking_metrics
from govplatform.evaluation.models import (
    Backend,
    BackendReport,
    Case,
    CaseResult,
    Dataset,
    EvaluationReport,
)
from govplatform.ingest.__main__ import _active_objects
from govplatform.ingest.es_index import elasticsearch_client, index_alias, sync_index
from govplatform.search.service import search


def code_fingerprint() -> str:
    root = Path(__file__).resolve().parents[3]
    files = [*Path(__file__).parent.glob("*.py")]
    for folder in ("search", "ingest", "knowledge", "db"):
        files.extend((root / "src/govplatform" / folder).glob("*.py"))
    files.extend(
        root / name
        for name in (
            "src/govplatform/embedding.py",
            "src/govplatform/model_cache.py",
            "src/govplatform/rerank_model.py",
            "pyproject.toml",
            "uv.lock",
        )
    )
    files.extend([root / "src/govplatform/db/schema.sql", root / "src/govplatform/config.py"])
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def evaluate_case(
    case: Case,
    backend: Backend,
    mapping: dict[str, str],
    forbidden: set[str],
) -> CaseResult:
    started = perf_counter()
    try:
        response = search(query=case.query, caller=EVALUATOR, limit=10, attempt=2)
        if any(hit.knowledge_id not in mapping for hit in response.results):
            raise ValueError("unexpected knowledge outside isolated corpus")
        expected_backend = "sqlite_fallback" if backend == "sqlite" else "elasticsearch"
        degraded = (
            response.retrieval_backend != expected_backend
            or response.retrieval_mode != "hybrid"
            or (backend == "elasticsearch" and response.relevance_grade == "unavailable")
        )
        ranked = list(
            dict.fromkeys(mapping.get(hit.knowledge_id, "unknown") for hit in response.results)
        )
        result = CaseResult(
            id=case.id,
            group=case.group,
            query=case.query,
            expected=case.relevant,
            ranked=ranked,
            status="degraded" if degraded else "ok",
            backend=response.retrieval_backend,
            mode=response.retrieval_mode,
            grade=response.relevance_grade,
            elapsed_ms=round((perf_counter() - started) * 1000, 3),
            lifecycle_violations=sorted(set(ranked) & forbidden),
        )
        if not degraded and case.relevant:
            result.recall_at_5, result.mrr_at_10 = ranking_metrics(ranked, case.relevant)
        if not degraded and not case.relevant and backend == "elasticsearch":
            result.no_answer_correct = response.relevance_grade == "insufficient" and not ranked
        return result
    except Exception as exc:
        return CaseResult(
            id=case.id,
            group=case.group,
            query=case.query,
            expected=case.relevant,
            status="error",
            error_type=type(exc).__name__,
            elapsed_ms=round((perf_counter() - started) * 1000, 3),
        )


def _remove_index(client: Elasticsearch, index: str, alias: str) -> None:
    if not alias.startswith("govplatform_eval_") or not index.startswith(alias + "_v"):
        raise ValueError("refusing to remove a non-evaluation index")
    client.indices.delete(index=index)


def run_backend(dataset: Dataset, backend: Backend, es_url: str | None) -> BackendReport:
    started = perf_counter()
    results: list[CaseResult] = []
    setup_ms, warmup_ms = 0.0, 0.0
    error_type = None
    try:
        with corpus(dataset, backend, es_url) as mapping:
            client, index, alias = None, None, index_alias()
            try:
                if backend == "elasticsearch":
                    client = elasticsearch_client()
                    index = sync_index(client, _active_objects())
                setup_ms = round((perf_counter() - started) * 1000, 3)
                warmup = perf_counter()
                search(query="retrieval warmup", caller=EVALUATOR, limit=10, attempt=2)
                warmup_ms = round((perf_counter() - warmup) * 1000, 3)
                forbidden = {doc.id for doc in dataset.documents if doc.state != "active"}
                results = [
                    evaluate_case(case, backend, mapping, forbidden) for case in dataset.cases
                ]
            finally:
                if client is not None:
                    try:
                        if index is not None:
                            _remove_index(client, index, alias)
                    finally:
                        client.close()
    except Exception as exc:
        error_type = type(exc).__name__
        if not results:
            results = [
                CaseResult(
                    id=case.id,
                    group=case.group,
                    query=case.query,
                    expected=case.relevant,
                    status="error",
                    elapsed_ms=0,
                    error_type=error_type,
                )
                for case in dataset.cases
            ]
    return BackendReport(
        requested_backend=backend,
        setup_ms=setup_ms,
        warmup_ms=warmup_ms,
        results=results,
        metrics=aggregate(results),
        error_type=error_type,
        group_metrics={
            group: aggregate([row for row in results if row.group == group])
            for group in sorted({case.group for case in dataset.cases})
        },
    )


def evaluate(path: Path, backends: list[Backend], es_url: str | None) -> EvaluationReport:
    content = path.read_bytes()
    dataset = Dataset.model_validate_json(content)
    return EvaluationReport(
        dataset_version=dataset.version,
        dataset_sha256=hashlib.sha256(content).hexdigest(),
        label_status=dataset.label_status,
        code_sha256=code_fingerprint(),
        configuration={
            "embedding": model_cache.MODEL_NAME,
            "embedding_revision": model_cache.MODEL_REVISION,
            "reranker": rerank_model.MODEL_NAME,
            "reranker_revision": rerank_model.MODEL_REVISION,
            "limit": 10,
            "attempt": 2,
            "offline": True,
        },
        backends=[run_backend(dataset, backend, es_url) for backend in backends],
        limitations=[
            "Public synthetic baseline with draft labels; not a held-out benchmark.",
            "No generated answers, automatic query rewriting or model-token accounting.",
            "SQLite has no relevance grader: unavailable is not scored as correct abstention.",
            "One unscored warmup per backend; setup includes fixture embedding/indexing.",
            "Small corpus and Chinese-oriented models; no claim of general multilingual quality.",
        ],
    )
