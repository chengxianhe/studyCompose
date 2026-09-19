from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from govplatform.config import db_path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    # 兼容阶段0/1时期已经建好的旧库（没有 embedding/embedding_model 列）；
    # 新库走 schema.sql 的 CREATE TABLE 就已经带了这两列，这里会因为列已
    # 存在而报错——只吞掉"列已存在"这一种错误，其他错误（比如数据库被
    # 锁）必须让它冒出来，不能当成"迁移已经做过了"悄悄放过。
    for column_ddl in (
        "ALTER TABLE knowledge_objects ADD COLUMN embedding BLOB",
        "ALTER TABLE knowledge_objects ADD COLUMN embedding_model TEXT",
    ):
        try:
            conn.execute(column_ddl)
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc):
                raise
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
