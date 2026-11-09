#!/usr/bin/env python3
"""Hash HEAD and all tracked/unignored files, including staged and untracked work."""

import hashlib
import os
from pathlib import Path
import subprocess


def fingerprint(root: Path) -> str:
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=root)

    digest = hashlib.sha256(git("rev-parse", "HEAD"))
    digest.update(git("diff", "--cached", "--binary", "HEAD"))
    paths = set(git("ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0"))
    for raw_path in sorted(paths - {b""}):
        path = root / os.fsdecode(raw_path)
        digest.update(raw_path + b"\0")
        if path.is_symlink():
            digest.update(b"link\0" + os.fsencode(os.readlink(path)))
        elif path.is_file():
            digest.update(b"file\0" + str(path.stat().st_mode & 0o777).encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        elif not path.exists():
            digest.update(b"deleted")
        else:
            raise ValueError(f"Unsupported repository entry: {path}")
        digest.update(b"\0")
    return digest.hexdigest()


if __name__ == "__main__":
    repository = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    print(fingerprint(repository))
