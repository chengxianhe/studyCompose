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

CREATE TABLE IF NOT EXISTS waivers (
  waiver_id    TEXT PRIMARY KEY,
  contract_id  TEXT NOT NULL,
  ac_id        TEXT NOT NULL,
  reason       TEXT NOT NULL,
  risk         TEXT NOT NULL,
  approved_by  TEXT NOT NULL,
  created_at   TEXT NOT NULL,
  expires_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_waivers_contract_ac
  ON waivers (contract_id, ac_id);

CREATE TABLE IF NOT EXISTS harness_runs (
  run_id                   TEXT PRIMARY KEY,
  contract_id              TEXT NOT NULL,
  status                   TEXT NOT NULL,
  repair_round             INTEGER NOT NULL,
  entry_gate_results_json  TEXT NOT NULL,
  acceptance_results_json  TEXT NOT NULL,
  repair_rounds_json       TEXT NOT NULL,
  escalation_reason        TEXT,
  started_by               TEXT NOT NULL,
  created_at               TEXT NOT NULL,
  updated_at                TEXT NOT NULL,
  delivered_at               TEXT
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

-- T-028 additive schema: existing databases retain all knowledge and governance records.
CREATE TABLE IF NOT EXISTS graph_sources (
  source_id TEXT PRIMARY KEY,
  locator TEXT NOT NULL,
  dedup_key TEXT NOT NULL,
  payload TEXT NOT NULL,
  UNIQUE(locator, dedup_key)
);

CREATE TABLE IF NOT EXISTS graph_relations (
  relation_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN ('derived_from','depends_on','supersedes')),
  subject_id TEXT NOT NULL REFERENCES knowledge_objects(knowledge_id),
  target_knowledge_id TEXT REFERENCES knowledge_objects(knowledge_id),
  target_source_id TEXT REFERENCES graph_sources(source_id),
  evidence_source_id TEXT NOT NULL REFERENCES graph_sources(source_id),
  status TEXT NOT NULL CHECK(status IN ('in_review','active','revoked')),
  payload TEXT NOT NULL,
  CHECK((kind='derived_from' AND target_source_id IS NOT NULL AND target_knowledge_id IS NULL)
    OR (kind!='derived_from' AND target_knowledge_id IS NOT NULL AND target_source_id IS NULL)),
  CHECK(subject_id != COALESCE(target_knowledge_id,''))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_graph_relation_live
  ON graph_relations(kind, subject_id, COALESCE(target_knowledge_id,''), COALESCE(target_source_id,''))
  WHERE status IN ('in_review','active');
CREATE INDEX IF NOT EXISTS idx_graph_subject ON graph_relations(subject_id,status,relation_id);
CREATE INDEX IF NOT EXISTS idx_graph_target ON graph_relations(target_knowledge_id,kind,status,relation_id);
CREATE INDEX IF NOT EXISTS idx_graph_source ON graph_relations(target_source_id,kind,status,relation_id);
