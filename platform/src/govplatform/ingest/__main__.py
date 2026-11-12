"""Build the derived ES child index from currently effective approved knowledge."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime

from elasticsearch import Elasticsearch, NotFoundError, TransportError

from govplatform.db.connection import get_connection
from govplatform.ingest.es_index import (
    elasticsearch_client,
    expected_index,
    index_alias,
    sync_index,
)
from govplatform.ingest.health import diagnose
from govplatform.knowledge import service as knowledge_service
from govplatform.knowledge import store as knowledge_store
from govplatform.knowledge.models import KnowledgeObject, KnowledgeStatus


def _active_objects() -> list[KnowledgeObject]:
    now = datetime.now(UTC)
    with get_connection() as conn:
        return [
            obj
            for obj, _emb in knowledge_store.list_by_status_with_embeddings(
                conn, KnowledgeStatus.ACTIVE
            )
            if knowledge_service.is_currently_valid(obj, now=now)
        ]


def _sync(client: Elasticsearch) -> dict[str, str | int]:
    index = sync_index(client, _active_objects())
    return {"index": index, "active_chunks": client.count(index=index_alias())["count"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("sync", "status", "watch", "doctor"))
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    if args.interval < 1.0:
        parser.error("--interval must be at least 1 second")
    with elasticsearch_client() as client:
        if args.action == "sync":
            print(json.dumps(_sync(client), sort_keys=True))
        elif args.action == "doctor":
            report = diagnose(client, _active_objects())
            print(json.dumps(report, sort_keys=True))
            if not report["ready"]:
                raise SystemExit(1)
        elif args.action == "status":
            expected = expected_index(_active_objects())
            try:
                current = list(client.indices.get_alias(name=index_alias()).keys())
            except NotFoundError:
                current = []
            status = {"expected": expected, "current": current, "ready": current == [expected]}
            print(json.dumps(status))
        else:
            last_index: str | None = None
            while True:
                try:
                    report = _sync(client)
                    if report["index"] != last_index:
                        print(json.dumps(report, sort_keys=True), flush=True)
                        last_index = str(report["index"])
                except TransportError as exc:
                    print(f"ES 同步等待服务恢复：{type(exc).__name__}", flush=True)
                time.sleep(args.interval)


if __name__ == "__main__":
    main()
