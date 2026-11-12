"""SQLite 一致性快照；恢复只写新路径，不覆盖正在使用的数据库。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from govplatform.config import db_path

TABLES = ("knowledge_objects", "contracts", "harness_runs", "waivers", "audit_events")
GRAPH_TABLES = ("graph_sources", "graph_relations")


def inspect_database(path: Path) -> dict[str, int]:
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity check failed")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite foreign key check failed")
        existing = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        graph_tables = tuple(table for table in GRAPH_TABLES if table in existing)
        if graph_tables and len(graph_tables) != len(GRAPH_TABLES):
            raise ValueError("incomplete graph schema")
        return {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (*TABLES, *graph_tables)
        }


def create_backup(source: Path, destination: Path) -> Path:
    """destination 是必须不存在的新目录，包含 database.sqlite 和 manifest.json。"""
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    target = destination / "database.sqlite"
    manifest = destination / "manifest.json"
    try:
        target.touch(mode=0o600, exist_ok=False)
        with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(target)) as dst:
                src.backup(dst)
        counts = inspect_database(target)
        manifest.write_text(
            json.dumps(
                {
                    "format_version": 1,
                    "created_at": datetime.now(UTC).isoformat(),
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "counts": counts,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        target.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        destination.rmdir()
        raise
    return destination


def restore_backup(snapshot: Path, destination: Path) -> dict[str, int]:
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    data = (snapshot / "database.sqlite").read_bytes()
    if manifest.get("format_version") != 1:
        raise ValueError("unsupported backup format")
    if hashlib.sha256(data).hexdigest() != manifest.get("sha256"):
        raise ValueError("backup checksum mismatch")
    # 独占创建：已有文件、符号链接或真实在线数据库一律拒绝覆盖。
    with destination.open("xb") as target:
        try:
            destination.chmod(0o600)
            target.write(data)
            target.flush()
            counts = inspect_database(destination)
            if counts != manifest.get("counts"):
                raise ValueError("backup row counts mismatch")
        except Exception:
            destination.unlink()
            raise
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    backup = sub.add_parser("create")
    backup.add_argument("destination", type=Path)
    backup.add_argument("--source", type=Path, default=db_path())
    restore = sub.add_parser("restore")
    restore.add_argument("snapshot", type=Path)
    restore.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.command == "create":
        print(create_backup(args.source, args.destination))
    else:
        print(json.dumps(restore_backup(args.snapshot, args.destination)))


if __name__ == "__main__":
    main()
