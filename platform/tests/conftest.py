from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from govplatform.identity.models import Agent, Human


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    db_file = tmp_path / "knowledge.db"
    monkeypatch.setenv("GOVPLAT_DB_PATH", str(db_file))
    yield


@pytest.fixture
def owner_human() -> Human:
    return Human(id="chengxianhe0@gmail.com")


@pytest.fixture
def claude_code_agent() -> Agent:
    return Agent(kind="claude-code", session_id="test-session-claude")


@pytest.fixture
def codex_agent() -> Agent:
    return Agent(kind="codex", session_id="test-session-codex")
