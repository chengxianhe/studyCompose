from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import NamedTuple

from govplatform.identity.models import Agent, Human, Principal
from govplatform.knowledge.models import (
    AuthorityLevel,
    KnowledgeObject,
    KnowledgeStatus,
    KnowledgeType,
)


class StoredEmbedding(NamedTuple):
    vector: bytes | None
    model: str | None


def insert(conn: sqlite3.Connection, obj: KnowledgeObject, embedding: StoredEmbedding) -> None:
    conn.execute(
        """
        INSERT INTO knowledge_objects (
            knowledge_id, title, type, body, source, author_json, owner,
            authority_level, status, version, effective_at, expire_at,
            tags_json, content_hash, created_at, updated_at, embedding,
            embedding_model
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            obj.knowledge_id,
            obj.title,
            obj.type.value,
            obj.body,
            obj.source,
            obj.author.model_dump_json(),
            obj.owner,
            obj.authority_level.value,
            obj.status.value,
            obj.version,
            obj.effective_at.isoformat() if obj.effective_at else None,
            obj.expire_at.isoformat() if obj.expire_at else None,
            json.dumps(obj.tags),
            obj.content_hash,
            obj.created_at.isoformat(),
            obj.updated_at.isoformat(),
            embedding.vector,
            embedding.model,
        ),
    )


def get(conn: sqlite3.Connection, knowledge_id: str) -> KnowledgeObject | None:
    row = conn.execute(
        "SELECT * FROM knowledge_objects WHERE knowledge_id = ?", (knowledge_id,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_object(row)


def list_by_status_with_embeddings(
    conn: sqlite3.Connection, status: KnowledgeStatus
) -> list[tuple[KnowledgeObject, StoredEmbedding]]:
    rows = conn.execute(
        "SELECT * FROM knowledge_objects WHERE status = ? ORDER BY created_at ASC",
        (status.value,),
    ).fetchall()
    return [
        (_row_to_object(row), StoredEmbedding(row["embedding"], row["embedding_model"]))
        for row in rows
    ]


def update_status(
    conn: sqlite3.Connection,
    knowledge_id: str,
    *,
    status: KnowledgeStatus,
    owner: str | None,
    updated_at: datetime,
) -> None:
    conn.execute(
        "UPDATE knowledge_objects SET status = ?, owner = ?, updated_at = ? WHERE knowledge_id = ?",
        (status.value, owner, updated_at.isoformat(), knowledge_id),
    )


def _row_to_object(row: sqlite3.Row) -> KnowledgeObject:
    author_data = json.loads(row["author_json"])
    author: Principal = (
        Human(**author_data) if author_data["principal_type"] == "human" else Agent(**author_data)
    )
    return KnowledgeObject(
        knowledge_id=row["knowledge_id"],
        title=row["title"],
        type=KnowledgeType(row["type"]),
        body=row["body"],
        source=row["source"],
        author=author,
        owner=row["owner"],
        authority_level=AuthorityLevel(row["authority_level"]),
        status=KnowledgeStatus(row["status"]),
        version=row["version"],
        effective_at=datetime.fromisoformat(row["effective_at"]) if row["effective_at"] else None,
        expire_at=datetime.fromisoformat(row["expire_at"]) if row["expire_at"] else None,
        tags=json.loads(row["tags_json"]),
        content_hash=row["content_hash"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
