from __future__ import annotations

import uuid

from govplatform.db.connection import get_connection
from govplatform.graph import store
from govplatform.graph._shared import audit, knowledge_ref, now, text
from govplatform.graph.models import GraphError, Relation, RelationKind
from govplatform.identity.models import Principal, resolve_principal


def propose(
    *,
    kind: RelationKind,
    subject_id: str,
    evidence_source_id: str,
    reason: str,
    applicability: str,
    caller: Principal,
    target_knowledge_id: str | None = None,
    target_source_id: str | None = None,
) -> Relation:
    principal = resolve_principal(caller)
    if kind not in ("derived_from", "depends_on", "supersedes"):
        raise GraphError("unknown relation kind")
    reason, applicability = text(reason, "reason"), text(applicability, "applicability")
    if kind == "derived_from":
        if not target_source_id or target_knowledge_id or target_source_id != evidence_source_id:
            raise GraphError("derived_from requires its source revision as target and evidence")
    elif not target_knowledge_id or target_source_id or target_knowledge_id == subject_id:
        raise GraphError("knowledge relations require distinct knowledge endpoints")
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        for key in (evidence_source_id, target_source_id):
            if key and store.get_source(conn, key) is None:
                raise GraphError("unknown source revision")
        subject = knowledge_ref(conn, subject_id)
        target = knowledge_ref(conn, target_knowledge_id) if target_knowledge_id else None
        duplicate = conn.execute(
            "SELECT 1 FROM graph_relations WHERE kind=? AND subject_id=? "
            "AND COALESCE(target_knowledge_id,'')=? AND COALESCE(target_source_id,'')=? "
            "AND status IN ('in_review','active') LIMIT 1",
            (kind, subject_id, target_knowledge_id or "", target_source_id or ""),
        ).fetchone()
        if duplicate:
            raise GraphError("relation already pending or active; revoke before replacing")
        obj = Relation(
            relation_id=uuid.uuid4().hex,
            kind=kind,
            subject=subject,
            target_knowledge=target,
            target_source_id=target_source_id,
            evidence_source_id=evidence_source_id,
            reason=reason,
            applicability=applicability,
            author=principal,
            created_at=now(),
            updated_at=now(),
        )
        store.insert_relation(conn, obj)
        audit(conn, principal, "graph.propose", obj.relation_id)
    return obj
