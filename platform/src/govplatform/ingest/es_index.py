"""Rebuildable Elasticsearch child index; SQLite remains the authority."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from typing import Any

import numpy as np
from elasticsearch import Elasticsearch, NotFoundError, helpers

from govplatform import embedding, model_cache
from govplatform.ingest.chunker import ChildChunk, chunk_knowledge
from govplatform.ingest.es_maintenance import discard_unpublished_target, prune_orphan_indices
from govplatform.knowledge.models import KnowledgeObject

_DEFAULT_INDEX_ALIAS = "govplatform_knowledge_chunks"
_INDEX_VERSION = "1"


def index_alias() -> str:
    return os.environ.get("GOVPLAT_ES_INDEX_ALIAS", _DEFAULT_INDEX_ALIAS)


def elasticsearch_client() -> Elasticsearch:
    url = os.environ.get("GOVPLAT_ES_URL", "http://127.0.0.1:9200")
    api_key = os.environ.get("GOVPLAT_ES_API_KEY")
    ca_certs = os.environ.get("GOVPLAT_ES_CA_CERTS")
    options: dict[str, Any] = {"request_timeout": 10, "max_retries": 0}
    if api_key:
        options["api_key"] = api_key
    if ca_certs:
        options["ca_certs"] = ca_certs
    return Elasticsearch(url, **options)


def _fingerprint(objects: Sequence[KnowledgeObject]) -> str:
    payload = {
        "index_version": _INDEX_VERSION,
        "embedding_model": embedding.MODEL_NAME,
        "embedding_revision": model_cache.MODEL_REVISION,
        "objects": sorted(
            (obj.knowledge_id, obj.version, obj.content_hash) for obj in objects
        ),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]


def expected_index(objects: Sequence[KnowledgeObject]) -> str:
    return f"{index_alias()}_v{_INDEX_VERSION}_{_fingerprint(objects)}"


class IndexNotReadyError(RuntimeError):
    """The offline worker has not published the current approved corpus."""


def require_ready_index(client: Elasticsearch, objects: Sequence[KnowledgeObject]) -> str:
    expected = expected_index(objects)
    try:
        current = list(client.indices.get_alias(name=index_alias()).keys())
    except NotFoundError as exc:
        raise IndexNotReadyError("知识子块索引尚未构建") from exc
    if current != [expected]:
        raise IndexNotReadyError("知识状态已变化，等待离线索引同步")
    return expected


def _mapping() -> dict[str, Any]:
    return {
        "dynamic": "strict",
        "properties": {
            "chunk_id": {"type": "keyword"},
            "parent_id": {"type": "keyword"},
            "parent_version": {"type": "integer"},
            "ordinal": {"type": "integer"},
            "heading_path": {"type": "keyword"},
            "text": {"type": "text", "analyzer": "cjk"},
            "bm25_field": {"type": "text", "analyzer": "cjk"},
            "source": {"type": "keyword"},
            "content_hash": {"type": "keyword"},
            "embedding_model": {"type": "keyword"},
            "embedding_revision": {"type": "keyword"},
            "knn_vector": {
                "type": "dense_vector",
                "dims": 512,
                "index": True,
                "similarity": "cosine",
            },
        },
    }


def _document(chunk: ChildChunk) -> dict[str, Any]:
    vector = np.frombuffer(embedding.embed(chunk.vector_text), dtype="float32")
    if len(vector) != 512:
        raise ValueError("embedding dimensions must be 512")
    return {
        "chunk_id": chunk.chunk_id,
        "parent_id": chunk.parent_id,
        "parent_version": chunk.parent_version,
        "ordinal": chunk.ordinal,
        "heading_path": list(chunk.heading_path),
        "text": chunk.text,
        "bm25_field": chunk.bm25_field,
        "source": chunk.source,
        "content_hash": chunk.content_hash,
        "embedding_model": embedding.MODEL_NAME,
        "embedding_revision": model_cache.MODEL_REVISION,
        "knn_vector": vector.tolist(),
    }


def sync_index(client: Elasticsearch, objects: Sequence[KnowledgeObject]) -> str:
    """Atomically switch the alias after a complete derived-index rebuild."""
    alias = index_alias()
    target = expected_index(objects)
    try:
        current = list(client.indices.get_alias(name=alias).keys())
    except NotFoundError:
        current = []
    if current == [target]:
        prune_orphan_indices(client, alias=alias, protected={target})
        return target
    try:
        if not client.indices.exists(index=target):
            client.indices.create(
                index=target,
                mappings=_mapping(),
                settings={"number_of_shards": 1, "number_of_replicas": 0},
            )
        chunks = [chunk for obj in objects for chunk in chunk_knowledge(obj)]
        if chunks:
            helpers.bulk(
                client,
                (
                    {"_index": target, "_id": chunk.chunk_id, "_source": _document(chunk)}
                    for chunk in chunks
                ),
                refresh="wait_for",
                raise_on_error=True,
            )
        actions: list[dict[str, Any]] = [
            {"remove_index": {"index": old}} for old in current if old != target
        ]
        actions.append({"add": {"index": target, "alias": alias}})
        client.indices.update_aliases(actions=actions)
    except Exception:
        try:
            discard_unpublished_target(client, target=target)
        except Exception:
            # The original build error is more useful; a later sync can prune the orphan.
            pass
        raise
    prune_orphan_indices(client, alias=alias, protected={target})
    return target
