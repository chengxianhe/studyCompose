from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from govplatform.backup import create_backup, inspect_database, restore_backup
from govplatform.config import db_path
from govplatform.db.connection import get_connection


def test_snapshot_restore_roundtrip_and_no_overwrite(tmp_path: Path) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO audit_events (occurred_at,principal_type,principal_id,action,"
            "request_json,result_summary) VALUES ('now','agent','codex','test','{}','ok')"
        )
    source = db_path()
    before = source.read_bytes()
    snapshot = create_backup(source, tmp_path / "snapshot")
    target = tmp_path / "restored.sqlite"
    assert restore_backup(snapshot, target) == inspect_database(source)
    assert inspect_database(target)["audit_events"] == 1
    with pytest.raises(FileExistsError):
        restore_backup(snapshot, source)
    with pytest.raises(FileExistsError):
        create_backup(source, snapshot)
    link = tmp_path / "link.sqlite"
    link.symlink_to(source)
    with pytest.raises(FileExistsError):
        restore_backup(snapshot, link)
    assert source.read_bytes() == before


def test_corrupt_or_incomplete_backups_refused(tmp_path: Path) -> None:
    with get_connection():
        pass
    snapshot = create_backup(db_path(), tmp_path / "snapshot")
    target = tmp_path / "target.sqlite"
    (snapshot / "database.sqlite").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        restore_backup(snapshot, target)
    assert not target.exists()
    manifest = json.loads((snapshot / "manifest.json").read_text())
    manifest["sha256"] = hashlib.sha256(b"corrupt").hexdigest()
    (snapshot / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(Exception, match="database"):
        restore_backup(snapshot, target)
    assert not target.exists()
    (snapshot / "manifest.json").unlink()
    with pytest.raises(FileNotFoundError):
        restore_backup(snapshot, target)


def test_missing_source_does_not_create_empty_backup(tmp_path: Path) -> None:
    destination = tmp_path / "snapshot"
    with pytest.raises(FileNotFoundError):
        create_backup(tmp_path / "missing.sqlite", destination)
    assert not destination.exists()
