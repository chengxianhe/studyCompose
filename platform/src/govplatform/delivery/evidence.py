from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

VerificationMode = Literal["android", "platform", "all"]


class EvidenceError(ValueError):
    """不完整、过期或与请求范围不符的验证证据。"""


class VerificationEvidence(BaseModel):
    repository: str
    directory: str
    mode: VerificationMode
    head: str
    fingerprint: str
    exit_code: int
    log_sha256: str


def current_fingerprint(repository: Path) -> str:
    return subprocess.check_output(
        [sys.executable, str(repository / "scripts/workspace_fingerprint.py")],
        cwd=repository,
        text=True,
    ).strip()


def read_evidence(
    repository: Path,
    directory: Path,
    mode: VerificationMode,
) -> VerificationEvidence:
    root = repository.resolve()
    parent = root / ".verification"
    if parent.is_symlink() or directory.is_symlink() or directory.resolve().parent != parent:
        raise EvidenceError("证据必须来自当前仓库 .verification 下的真实目录")
    directory = directory.resolve()
    names = (
        "mode.txt",
        "head.txt",
        "fingerprint-before.txt",
        "fingerprint-after.txt",
        "exit-code.txt",
        "output.log",
        "status.txt",
    )
    for name in names:
        path = directory / name
        if not path.is_file() or path.is_symlink():
            raise EvidenceError(f"缺少完整的验证证据文件：{name}")
    if (directory / "mode.txt").read_text().strip() != mode:
        raise EvidenceError("验证范围不匹配，不能用 platform/workflow 代替 android/all")
    head = (directory / "head.txt").read_text().strip()
    actual_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    before = (directory / "fingerprint-before.txt").read_text().strip()
    after = (directory / "fingerprint-after.txt").read_text().strip()
    if head != actual_head or before != after or after != current_fingerprint(root):
        raise EvidenceError("HEAD 或源码已变化；请重新运行统一验证")
    try:
        exit_code = int((directory / "exit-code.txt").read_text().strip())
    except ValueError as exc:
        raise EvidenceError("退出码不是整数") from exc
    if not 0 <= exit_code <= 255:
        raise EvidenceError("退出码超出范围")
    log = directory / "output.log"
    if not log.stat().st_size:
        raise EvidenceError("验证日志为空")
    with log.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return VerificationEvidence(
        repository=str(root),
        directory=str(directory),
        mode=mode,
        head=head,
        fingerprint=after,
        exit_code=exit_code,
        log_sha256=digest,
    )


def evidence_summary(evidence: VerificationEvidence) -> str:
    # 保存可核对位置与摘要，不把可能包含敏感内容的完整日志写入数据库。
    return json.dumps(evidence.model_dump(), ensure_ascii=False, sort_keys=True)
