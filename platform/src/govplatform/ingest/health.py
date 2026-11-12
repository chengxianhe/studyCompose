"""Local search readiness report without changing knowledge or indices."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from elasticsearch import ApiError, Elasticsearch, NotFoundError, TransportError

from govplatform import model_cache, rerank_model
from govplatform.ingest.es_index import expected_index, index_alias
from govplatform.knowledge.models import KnowledgeObject

_PLATFORM_ROOT = Path(__file__).resolve().parents[3]


def _models_ready() -> tuple[bool, bool]:
    try:
        model_cache.verify_snapshot(model_cache.snapshot_directory())
        embedding_ready = True
    except (model_cache.ModelCacheError, OSError):
        embedding_ready = False
    try:
        rerank_model.verify_snapshot(rerank_model.snapshot_directory())
        reranker_ready = True
    except (rerank_model.RerankModelError, OSError):
        reranker_ready = False
    return embedding_ready, reranker_ready


def diagnose(client: Elasticsearch, objects: list[KnowledgeObject]) -> dict[str, Any]:
    """Report cache, disk, cluster, and current corpus readiness."""
    usage = shutil.disk_usage(_PLATFORM_ROOT)
    embedding_ready, reranker_ready = _models_ready()
    report: dict[str, Any] = {
        "ready": False,
        "embedding_ready": embedding_ready,
        "reranker_ready": reranker_ready,
        "disk_free_gib": round(usage.free / 1024**3, 1),
        "disk_used_percent": round(100 * usage.used / usage.total, 1),
        "es_reachable": False,
        "cluster_status": None,
        "index_ready": False,
    }
    try:
        health = client.cluster.health()
        report["es_reachable"] = True
        report["cluster_status"] = health["status"]
        try:
            current = list(client.indices.get_alias(name=index_alias()).keys())
        except NotFoundError:
            current = []
        report["index_ready"] = current == [expected_index(objects)]
    except (ApiError, TransportError, OSError):
        return report
    report["ready"] = (
        embedding_ready
        and reranker_ready
        and report["cluster_status"] != "red"
        and report["index_ready"]
    )
    return report
