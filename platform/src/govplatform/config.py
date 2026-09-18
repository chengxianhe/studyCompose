from __future__ import annotations

import os
from pathlib import Path

ALLOWED_AGENT_KINDS: frozenset[str] = frozenset({"claude-code", "codex"})

OWNER_HUMAN_ID: str = os.environ.get("GOVPLAT_OWNER_ID", "chengxianhe0@gmail.com")

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / ".data" / "knowledge.db"


def db_path() -> Path:
    override = os.environ.get("GOVPLAT_DB_PATH")
    if override:
        return Path(override)
    return _DEFAULT_DB_PATH
