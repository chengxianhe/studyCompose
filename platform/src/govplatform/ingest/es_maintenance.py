"""Safely remove unpublished, old derived Elasticsearch indices."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from elasticsearch import Elasticsearch, NotFoundError

_ORPHAN_GRACE = timedelta(hours=1)


def discard_unpublished_target(client: Elasticsearch, *, target: str) -> bool:
    """Remove a failed build only when no alias points to it."""
    try:
        details = client.indices.get(index=target)
    except NotFoundError:
        return False
    if details[target].get("aliases"):
        return False
    client.indices.delete(index=target)
    return True


def prune_orphan_indices(
    client: Elasticsearch,
    *,
    alias: str,
    protected: set[str],
    now: datetime | None = None,
) -> list[str]:
    """Remove only this alias's unaliased indices older than the build grace period."""
    try:
        indices = client.indices.get(index=f"{alias}_v*")
    except NotFoundError:
        return []
    cutoff_ms = int(((now or datetime.now(UTC)) - _ORPHAN_GRACE).timestamp() * 1000)
    removed: list[str] = []
    for name, details in indices.items():
        if name in protected or details.get("aliases"):
            continue
        created_at = details.get("settings", {}).get("index", {}).get("creation_date")
        if created_at is None or int(created_at) > cutoff_ms:
            continue
        client.indices.delete(index=name)
        removed.append(name)
    return removed
