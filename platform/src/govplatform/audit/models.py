from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AuditEvent(BaseModel):
    id: int | None = None
    occurred_at: datetime
    principal_type: str
    principal_id: str
    session_id: str | None
    action: str
    knowledge_id: str | None
    knowledge_version: int | None
    request_json: str
    result_summary: str
