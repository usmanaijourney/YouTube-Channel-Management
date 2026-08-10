-- Adapted from architecture doc §6 (Postgres) to SQLite for the Phase 0 MVP.
-- No RLS/sharding yet (single-channel MVP) — JSONB -> TEXT (JSON string), TIMESTAMPTZ -> TEXT (ISO8601).

CREATE TABLE IF NOT EXISTS channels (
  channel_id          TEXT PRIMARY KEY,
  name                TEXT NOT NULL,
  niche               TEXT,
  status              TEXT CHECK (status IN ('active','paused','error','onboarding')),
  youtube_channel_ref TEXT,
  created_at          TEXT DEFAULT (datetime('now')),
  schedule_json       TEXT
);

CREATE TABLE IF NOT EXISTS system_events (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id TEXT REFERENCES channels(channel_id),
  event_type TEXT,
  severity   TEXT CHECK (severity IN ('info','warning','critical')),
  payload    TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
  task_id    TEXT PRIMARY KEY,
  channel_id TEXT NOT NULL,
  state      TEXT NOT NULL,
  topic      TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  metadata   TEXT
);

CREATE TABLE IF NOT EXISTS task_events (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id    TEXT REFERENCES tasks(task_id),
  from_state TEXT,
  to_state   TEXT,
  agent_id   TEXT,
  payload    TEXT,
  error      TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agents (
  agent_id       TEXT PRIMARY KEY,
  channel_id     TEXT NOT NULL,
  agent_type     TEXT,
  status         TEXT,
  last_heartbeat TEXT,
  last_success   TEXT,
  last_failure   TEXT,
  failure_count  INTEGER DEFAULT 0,
  avg_exec_ms    INTEGER,
  retry_count    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS videos (
  video_id         TEXT PRIMARY KEY,
  task_id          TEXT REFERENCES tasks(task_id),
  channel_id       TEXT NOT NULL,
  youtube_video_id TEXT,
  youtube_url      TEXT,
  title            TEXT,
  status           TEXT,
  metrics          TEXT,
  created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cost_ledger (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id TEXT,
  task_id    TEXT,
  provider   TEXT,
  cost_usd   REAL,
  created_at TEXT DEFAULT (datetime('now'))
);
