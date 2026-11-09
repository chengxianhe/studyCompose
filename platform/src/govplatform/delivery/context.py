"""One immutable admission record per run, stored in the existing audit journal."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.db.connection import get_connection
from govplatform.delivery.evidence import (
    EvidenceError,
    VerificationEvidence,
    VerificationMode,
    current_fingerprint,
    read_evidence,
)
from govplatform.delivery.snapshot import FileSnapshot, capture, git
from govplatform.harness import store
from govplatform.harness._shared import now
from govplatform.harness.models import HarnessStatus
from govplatform.identity.models import Agent, resolve_principal


class ExecutionContext(BaseModel):
    run_id: str
    contract_id: str
    repository: str
    mode: VerificationMode
    baseline: VerificationEvidence
    snapshot: str
    snapshot_sha256: str
    created_at: datetime
    session_id: str


def get_context(run_id: str) -> ExecutionContext | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT request_json FROM audit_events WHERE action = 'delivery.prepare' "
            "AND json_extract(request_json, '$.run_id') = ? ORDER BY id LIMIT 1",
            (run_id,),
        ).fetchone()
    return ExecutionContext.model_validate_json(row[0]) if row else None


def prepare(
    *,
    repository: Path,
    directory: Path,
    mode: VerificationMode,
    run_id: str,
    caller: Agent,
) -> ExecutionContext:
    resolve_principal(caller)
    root = repository.resolve()
    with get_connection() as conn:
        run = store.get(conn, run_id)
    if run is None or run.status not in (HarnessStatus.DEVELOPING, HarnessStatus.REPAIRING):
        raise EvidenceError("运行必须已由用户启动，且处于开发或修复状态")
    # A repeated prepare resumes the original record; it never replaces the baseline.
    previous = get_context(run_id)
    if previous is not None:
        if previous.repository != str(root) or previous.mode != mode:
            raise EvidenceError("运行已绑定其他仓库或验证范围")
        read_snapshot(previous)
        return previous
    evidence = read_evidence(root, directory, mode)
    if evidence.exit_code != 0:
        raise EvidenceError("准入基线检查失败，不能记录为已准入")
    snapshot = capture(root)
    payload = TypeAdapter(dict[str, FileSnapshot]).dump_json(snapshot)
    existing_diff = git(root, "diff", "--binary", "HEAD")
    existing_index = git(root, "diff", "--cached", "--binary", "HEAD")
    status = git(root, "status", "--short")
    if current_fingerprint(root) != evidence.fingerprint:
        raise EvidenceError("采集准入快照期间源码变化，请重试")
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        run = store.get(conn, run_id)
        if run is None or run.status not in (HarnessStatus.DEVELOPING, HarnessStatus.REPAIRING):
            raise EvidenceError("运行必须已由用户启动，且处于开发或修复状态")
        duplicate = conn.execute(
            "SELECT 1 FROM audit_events WHERE action = 'delivery.prepare' "
            "AND json_extract(request_json, '$.run_id') = ?",
            (run_id,),
        ).fetchone()
        if duplicate:
            raise EvidenceError("另一个执行者已记录准入，请重新读取")
        target = root / ".verification" / f"session-{uuid.uuid4().hex}"
        target.mkdir(mode=0o700)
        path = target / "snapshot.json"
        path.write_bytes(payload)
        (target / "existing-wip.patch").write_text(existing_diff)
        (target / "existing-index.patch").write_text(existing_index)
        (target / "status.txt").write_text(status)
        if current_fingerprint(root) != evidence.fingerprint:
            raise EvidenceError("准入材料必须被 Git 忽略；快照不一致，未记录准入")
        context = ExecutionContext(
            run_id=run_id,
            contract_id=run.contract_id,
            repository=str(root),
            mode=mode,
            baseline=evidence,
            snapshot=str(path),
            snapshot_sha256=hashlib.sha256(payload).hexdigest(),
            created_at=now(),
            session_id=caller.session_id,
        )
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=context.created_at,
                principal_type="agent",
                principal_id=caller.kind,
                session_id=caller.session_id,
                action="delivery.prepare",
                knowledge_id=None,
                knowledge_version=None,
                request_json=context.model_dump_json(),
                result_summary="当前接续基线已记录，不代表此前工作具有准入证据",
            ),
        )
    return context


def read_snapshot(context: ExecutionContext) -> dict[str, FileSnapshot]:
    path = Path(context.snapshot)
    parent = Path(context.repository) / ".verification"
    if path.is_symlink() or not path.resolve().is_relative_to(parent.resolve()):
        raise EvidenceError("准入快照位置不匹配")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != context.snapshot_sha256:
        raise EvidenceError("准入快照已变化")
    return TypeAdapter(dict[str, FileSnapshot]).validate_json(payload)
