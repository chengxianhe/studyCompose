CREATE TABLE IF NOT EXISTS knowledge_objects (
  knowledge_id    TEXT PRIMARY KEY,
  title           TEXT NOT NULL,
  type            TEXT NOT NULL,
  body            TEXT NOT NULL,
  source          TEXT NOT NULL,
  author_json     TEXT NOT NULL,
  owner           TEXT,
  authority_level TEXT NOT NULL,
  status          TEXT NOT NULL,
  version         INTEGER NOT NULL,
  effective_at    TEXT,
  expire_at       TEXT,
  tags_json       TEXT NOT NULL,
  content_hash    TEXT NOT NULL,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  embedding       BLOB,
  embedding_model TEXT
);

CREATE TABLE IF NOT EXISTS contracts (
  contract_id              TEXT PRIMARY KEY,
  title                    TEXT NOT NULL,
  goal                     TEXT NOT NULL,
  scope                    TEXT NOT NULL,
  out_of_scope             TEXT,
  author_json              TEXT NOT NULL,
  status                   TEXT NOT NULL,
  version                  INTEGER NOT NULL,
  acceptance_criteria_json TEXT NOT NULL,
  test_cases_json          TEXT NOT NULL,
  knowledge_refs_json      TEXT NOT NULL,
  knowledge_snapshots_json TEXT NOT NULL DEFAULT '[]',
  risks_json                TEXT NOT NULL,
  open_questions_json       TEXT NOT NULL,
  frozen_by                 TEXT,
  frozen_at                  TEXT,
  created_at                  TEXT NOT NULL,
  updated_at                   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  occurred_at       TEXT NOT NULL,
  principal_type    TEXT NOT NULL,
  principal_id      TEXT NOT NULL,
  session_id        TEXT,
  action            TEXT NOT NULL,
  knowledge_id      TEXT,
  knowledge_version INTEGER,
  request_json      TEXT NOT NULL,
  result_summary    TEXT NOT NULL
);
