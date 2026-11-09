"""Capture the existing worktree, including untracked files, without changing Git."""

from __future__ import annotations

import base64
import difflib
import os
import subprocess
from pathlib import Path

from pydantic import BaseModel

from govplatform.delivery.evidence import EvidenceError


class FileSnapshot(BaseModel):
    kind: str
    mode: int = 0
    content: str = ""


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True)


def capture(root: Path) -> dict[str, FileSnapshot]:
    names = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    result: dict[str, FileSnapshot] = {}
    for name in sorted(set(names.split("\0")) - {""}):
        path = root / name
        if path.is_symlink():
            result[name] = FileSnapshot(kind="link", content=os.readlink(path))
        elif path.is_file():
            if not path.resolve().is_relative_to(root):
                raise EvidenceError(f"工作区文件指向仓库外：{name}")
            result[name] = FileSnapshot(
                kind="file",
                mode=path.stat().st_mode & 0o777,
                content=base64.b64encode(path.read_bytes()).decode("ascii"),
            )
        elif path.exists():
            raise EvidenceError(f"无法记录工作区条目：{name}")
        else:
            result[name] = FileSnapshot(kind="deleted")
    return result


def changes(before: dict[str, FileSnapshot], after: dict[str, FileSnapshot]) -> str:
    parts: list[str] = []
    for name in sorted(before.keys() | after.keys()):
        old = before.get(name, FileSnapshot(kind="absent"))
        new = after.get(name, FileSnapshot(kind="absent"))
        if old == new:
            continue
        parts.append(f"\n--- {name}: {old.kind}/{old.mode:o} -> {new.kind}/{new.mode:o}\n")
        try:
            texts = []
            for item in (old, new):
                value = (
                    base64.b64decode(item.content).decode("utf-8")
                    if item.kind == "file"
                    else item.content
                )
                if "\0" in value:
                    raise UnicodeError("binary")
                texts.append(value.splitlines(keepends=True))
            parts.extend(
                difflib.unified_diff(
                    texts[0], texts[1], fromfile=f"before/{name}", tofile=f"after/{name}"
                )
            )
        except UnicodeError:
            parts.append("Binary content changed; inspect snapshot.json.\n")
    return "".join(parts) or "No worktree file changes since prepare.\n"
