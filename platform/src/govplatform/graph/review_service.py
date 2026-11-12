from __future__ import annotations

from govplatform.db.connection import get_connection
from govplatform.fingerprints import fingerprint
from govplatform.graph import store
from govplatform.graph._shared import audit, now, snapshot, text, warnings
from govplatform.graph.models import GraphError, Relation
from govplatform.identity.models import (
    Human,
    Principal,
    PrincipalNotAllowedError,
    resolve_principal,
)


def review(
    *,
    relation_id: str,
    caller: Principal,
    expected_snapshot: str,
    action: str,
    reason: str = "",
) -> Relation:
    principal = resolve_principal(caller)
    if not isinstance(principal, Human):
        raise PrincipalNotAllowedError("only the human owner can review relations")
    if action not in ("approve", "revoke"):
        raise GraphError("unknown review action")
    if action == "revoke":
        reason = text(reason, "revocation_reason")
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        obj = store.get_relation(conn, relation_id)
        if obj is None:
            raise GraphError("unknown relation")
        if fingerprint(snapshot(conn, obj)) != expected_snapshot:
            raise GraphError("relation or endpoints changed; refresh and review again")
        if action == "approve":
            if obj.status != "in_review" or any(
                issue != "relation_in_review" for issue in warnings(conn, obj)
            ):
                raise GraphError("relation must be pending with unchanged valid endpoints")
            if obj.kind == "supersedes":
                assert obj.target_knowledge is not None
                cycle = conn.execute(
                    "WITH RECURSIVE seen(id) AS (VALUES(?) UNION "
                    "SELECT r.target_knowledge_id FROM graph_relations r JOIN seen s "
                    "ON r.subject_id=s.id WHERE r.kind='supersedes' AND r.status='active') "
                    "SELECT 1 FROM seen WHERE id=? LIMIT 1",
                    (obj.target_knowledge.knowledge_id, obj.subject.knowledge_id),
                ).fetchone()
                if cycle:
                    raise GraphError("supersedes cycle rejected")
            obj = obj.model_copy(
                update={"status": "active", "approved_by": principal.id, "updated_at": now()}
            )
        else:
            if obj.status == "revoked":
                raise GraphError("relation already revoked")
            obj = obj.model_copy(
                update={
                    "status": "revoked",
                    "revoked_by": principal.id,
                    "revocation_reason": reason,
                    "updated_at": now(),
                }
            )
        store.save_relation(conn, obj)
        audit(conn, principal, "graph." + action, obj.relation_id)
    return obj
