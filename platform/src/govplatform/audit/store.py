from __future__ import annotations

import sqlite3
from datetime import datetime

from govplatform.audit.models import AuditEvent


def insert_audit_event(conn: sqlite3.Connection, event: AuditEvent) -> int:
    cursor = conn.execute(
        """
        INSERT INTO audit_events (
            occurred_at, principal_type, principal_id, session_id,
            action, knowledge_id, knowledge_version, request_json, result_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.occurred_at.isoformat(),
            event.principal_type,
            event.principal_id,
            event.session_id,
            event.action,
            event.knowledge_id,
            event.knowledge_version,
            event.request_json,
            event.result_summary,
        ),
    )
    row_id = cursor.lastrowid
    assert row_id is not None
    return row_id


def list_audit_events(conn: sqlite3.Connection) -> list[AuditEvent]:
    rows = conn.execute("SELECT * FROM audit_events ORDER BY id ASC").fetchall()
    return [_row_to_event(row) for row in rows]


def _row_to_event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        id=row["id"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        principal_type=row["principal_type"],
        principal_id=row["principal_id"],
        session_id=row["session_id"],
        action=row["action"],
        knowledge_id=row["knowledge_id"],
        knowledge_version=row["knowledge_version"],
        request_json=row["request_json"],
        result_summary=row["result_summary"],
    )
