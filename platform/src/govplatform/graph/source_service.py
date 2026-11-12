from __future__ import annotations

import re
import uuid
from urllib.parse import urlsplit

from govplatform.db.connection import get_connection
from govplatform.graph import store
from govplatform.graph._shared import audit, now, text
from govplatform.graph.models import GraphError, SourceRevision
from govplatform.identity.models import Principal, resolve_principal


def register(
    *,
    locator: str,
    caller: Principal,
    content_hash: str | None = None,
    version_label: str | None = None,
    idempotency_key: str | None = None,
    attribution: str | None = None,
    license_note: str | None = None,
) -> SourceRevision:
    principal = resolve_principal(caller)
    locator = text(locator, "locator", 2000)
    try:
        parsed = urlsplit(locator)
        if parsed.username is not None or parsed.password is not None:
            raise GraphError("source locator must not contain credentials")
    except ValueError as exc:
        raise GraphError("invalid locator") from exc
    if content_hash is not None:
        content_hash = content_hash.lower()
        if not re.fullmatch("[0-9a-f]{64}", content_hash):
            raise GraphError("content_hash must be SHA-256 hex")
    if content_hash is None and not idempotency_key:
        raise GraphError("unknown digest requires an explicit idempotency_key")
    version_label = text(version_label, "version_label", 200) if version_label else None
    attribution = text(attribution, "attribution") if attribution else None
    license_note = text(license_note, "license_note") if license_note else None
    dedup_key = (
        "sha256:" + content_hash
        if content_hash
        else "request:" + text(idempotency_key or "", "idempotency_key", 200)
    )
    obj = SourceRevision(
        source_id=uuid.uuid4().hex,
        locator=locator,
        content_hash=content_hash,
        version_label=version_label,
        attribution=attribution,
        license_note=license_note,
        author=principal,
        observed_at=now(),
    )
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT source_id FROM graph_sources WHERE locator=? AND dedup_key=?",
            (locator, dedup_key),
        ).fetchone()
        if row:
            existing = store.get_source(conn, row[0])
            assert existing is not None
            if content_hash is None and (
                existing.version_label,
                existing.attribution,
                existing.license_note,
            ) != (version_label, attribution, license_note):
                raise GraphError("idempotency_key already used for different metadata")
            audit(conn, principal, "graph.source.reused", existing.source_id)
            return existing
        conn.execute(
            "INSERT INTO graph_sources VALUES (?,?,?,?)",
            (obj.source_id, locator, dedup_key, obj.model_dump_json()),
        )
        audit(conn, principal, "graph.source.register", obj.source_id)
    return obj
