"""A review packet describes observed changes; it does not grant approval."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from pydantic import TypeAdapter

from govplatform.audit.models import AuditEvent
from govplatform.audit.store import insert_audit_event
from govplatform.contract.models import Contract, VerificationType
from govplatform.db.connection import get_connection
from govplatform.delivery.context import ExecutionContext, read_snapshot
from govplatform.delivery.evidence import EvidenceError, VerificationEvidence, current_fingerprint
from govplatform.delivery.snapshot import FileSnapshot, capture, git
from govplatform.delivery.snapshot import changes as worktree_changes
from govplatform.harness._shared import now
from govplatform.harness.models import AcceptanceResult, HarnessRun
from govplatform.identity.models import Agent


def review_packet(
    context: ExecutionContext,
    contract: Contract,
    evidence: VerificationEvidence,
    results: list[AcceptanceResult],
    limitations: str,
) -> Path:
    root = Path(context.repository)
    before = read_snapshot(context)
    after = capture(root)
    index = git(root, "diff", "--cached", "--binary", "HEAD")
    status = git(root, "status", "--short")
    if current_fingerprint(root) != evidence.fingerprint:
        raise EvidenceError("生成审查材料期间源码变化")
    folder = root / ".verification" / f"review-{uuid.uuid4().hex}"
    folder.mkdir(mode=0o700)
    (folder / "changes.patch").write_text(worktree_changes(before, after))
    (folder / "current-index.patch").write_text(index)
    (folder / "status.txt").write_text(status)
    (folder / "snapshot.json").write_bytes(TypeAdapter(dict[str, FileSnapshot]).dump_json(after))
    data = {
        "run_id": context.run_id,
        "contract": contract.model_dump(mode="json"),
        "admission": context.model_dump(mode="json"),
        "verification": evidence.model_dump(),
        "agent_results": [r.model_dump(mode="json") for r in results],
        "limitations": limitations,
        "approval": "pending",
    }
    (folder / "report.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    manual = [
        ac.ac_id
        for ac in contract.acceptance_criteria
        if ac.verification_type == VerificationType.MANUAL_EVIDENCE
    ]
    lines = [
        f"# {contract.title} — 待人工审查",
        "",
        f"运行：`{context.run_id}`；契约：`{context.contract_id}`。",
        f"范围：{contract.scope}",
        f"不在范围内：{contract.out_of_scope or '见契约'}",
        "",
        f"当前源码指纹：`{evidence.fingerprint}`；HEAD：`{evidence.head}`。",
        f"统一检查：`{evidence.mode}`，退出码 `{evidence.exit_code}`。",
        f"日志：{evidence.directory}/output.log；SHA-256：`{evidence.log_sha256}`。",
        "",
        f"准入与既有 WIP：{Path(context.snapshot).parent}（当前接续起点，非追溯补造）。",
        "本次相对准入的差异：changes.patch；完整当前快照：snapshot.json；暂存区：current-index.patch。",
        "",
        "## 自动项（Agent 提交，语义是否充分仍需审查）",
        "",
        "统一检查失败，以下说明不计为验收通过。"
        if evidence.exit_code
        else "实际入库状态见 outcome.json 与运行状态。",
        *[f"- {r.ac_id}: {'通过' if r.passed else '失败'}；{r.evidence_summary}" for r in results],
        "",
        f"待人工项：{', '.join(manual) or '最终交付确认'}。",
        "",
        "## 已知风险与未验证项",
        "",
        limitations,
        "",
        "知识沉淀：由执行者搜索去重后提交提案并记入任务记录；本命令不自动批准。",
        "",
        "人工意见在现有审核页提交；自动检查通过不代表人工已验收。",
        "",
    ]
    (folder / "review.md").write_text("\n".join(lines))
    return folder


def record_outcome(folder: Path, run: HarnessRun) -> None:
    (folder / "outcome.json").write_text(run.model_dump_json(indent=2) + "\n")


def register_packet(folder: Path, run_id: str, caller: Agent) -> None:
    with get_connection() as conn:
        insert_audit_event(
            conn,
            AuditEvent(
                occurred_at=now(),
                principal_type="agent",
                principal_id=caller.kind,
                session_id=caller.session_id,
                action="delivery.review_packet",
                knowledge_id=None,
                knowledge_version=None,
                request_json=json.dumps({"run_id": run_id, "directory": str(folder)}),
                result_summary="审查材料已生成；提交结果和实际状态以 outcome.json 与 Harness 为准",
            ),
        )


def latest_packet(run_id: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT request_json FROM audit_events WHERE action = 'delivery.review_packet' "
            "AND json_extract(request_json, '$.run_id') = ? ORDER BY id DESC LIMIT 1",
            (run_id,),
        ).fetchone()
    return str(json.loads(row[0])["directory"]) if row else None
