-- Dashboard "Foundation" phase additions, per the platform spec's data model
-- (users/roles/permissions deliberately excluded — single-operator, §-scoped
-- decision; see project memory / conversation for rationale).

CREATE TABLE IF NOT EXISTS system_health (
  service_name    TEXT PRIMARY KEY,
  status          TEXT NOT NULL,   -- 'healthy' | 'error' | 'mocked'
  last_check_at   TEXT,
  last_success_at TEXT,
  response_time_ms INTEGER,
  error_count     INTEGER DEFAULT 0,
  last_error      TEXT
);

CREATE TABLE IF NOT EXISTS schedules (
  channel_id          TEXT PRIMARY KEY REFERENCES channels(channel_id),
  enabled             INTEGER NOT NULL DEFAULT 1,
  preferred_hours_utc TEXT,   -- JSON list, e.g. "[9, 16]"
  last_run_at         TEXT,
  last_run_status     TEXT    -- 'idle' | 'running' | 'completed' | 'failed'
);

-- Schema only this phase — no write endpoints exist yet to populate it.
-- Wired up when action endpoints (retry/pause/resume) land.
CREATE TABLE IF NOT EXISTS audit_logs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  actor         TEXT NOT NULL,
  action        TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id   TEXT,
  details       TEXT,
  created_at    TEXT DEFAULT (datetime('now'))
);
