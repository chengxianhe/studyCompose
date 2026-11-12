from __future__ import annotations

import sqlite3

from govplatform.graph.models import Relation, SourceRevision


def get_source(conn: sqlite3.Connection, key: str) -> SourceRevision | None:
    row = conn.execute("SELECT payload FROM graph_sources WHERE source_id=?", (key,)).fetchone()
    return SourceRevision.model_validate_json(row[0]) if row else None


def get_relation(conn: sqlite3.Connection, key: str) -> Relation | None:
    row = conn.execute("SELECT payload FROM graph_relations WHERE relation_id=?", (key,)).fetchone()
    return Relation.model_validate_json(row[0]) if row else None


def insert_relation(conn: sqlite3.Connection, obj: Relation) -> None:
    conn.execute(
        "INSERT INTO graph_relations (relation_id,kind,subject_id,target_knowledge_id,"
        "target_source_id,evidence_source_id,status,payload) VALUES (?,?,?,?,?,?,?,?)",
        (
            obj.relation_id,
            obj.kind,
            obj.subject.knowledge_id,
            obj.target_knowledge.knowledge_id if obj.target_knowledge else None,
            obj.target_source_id,
            obj.evidence_source_id,
            obj.status,
            obj.model_dump_json(),
        ),
    )


def save_relation(conn: sqlite3.Connection, obj: Relation) -> None:
    conn.execute(
        "UPDATE graph_relations SET status=?,payload=? WHERE relation_id=?",
        (obj.status, obj.model_dump_json(), obj.relation_id),
    )


def adjacent(conn: sqlite3.Connection, key: str, *, reverse: bool, limit: int) -> list[Relation]:
    category, identity = key.split(":", 1)
    if reverse:
        column = "target_source_id" if category == "source" else "target_knowledge_id"
        kind = "derived_from" if category == "source" else "depends_on"
        condition = (
            f"{column}=? AND kind=? AND status IN ('active','revoked') "
            "AND json_extract(payload,'$.approved_by') IS NOT NULL"
        )
        params: tuple[str, ...] = (identity, kind)
    elif category == "knowledge":
        condition, params = "subject_id=? AND status='active'", (identity,)
    else:
        return []
    rows = conn.execute(
        "SELECT payload FROM graph_relations WHERE " + condition + " ORDER BY relation_id LIMIT ?",
        (*params, limit),
    ).fetchall()
    return [Relation.model_validate_json(row[0]) for row in rows]


def replacements(conn: sqlite3.Connection, key: str, limit: int) -> list[Relation]:
    rows = conn.execute(
        "SELECT payload FROM graph_relations WHERE target_knowledge_id=? "
        "AND kind='supersedes' AND status='active' ORDER BY relation_id LIMIT ?",
        (key, limit),
    ).fetchall()
    return [Relation.model_validate_json(row[0]) for row in rows]
