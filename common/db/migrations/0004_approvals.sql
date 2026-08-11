-- Human approval gates, moved off the terminal (doc §20's gates were CLI
-- input() calls, which is why the pipeline could only run at an operator's desk).
--
-- The pipeline writes a 'pending' row and blocks on it; the dashboard decides it.
-- One row per (task, stage): a gate is asked exactly once per task, and the
-- UNIQUE constraint is what makes a double-submit from the UI harmless.
CREATE TABLE IF NOT EXISTS approvals (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id      TEXT NOT NULL REFERENCES tasks(task_id),
  channel_id   TEXT NOT NULL REFERENCES channels(channel_id),
  stage        TEXT NOT NULL,   -- 'topic' | 'script' | 'pre_upload'
  status       TEXT NOT NULL,   -- 'pending' | 'approved' | 'rejected' | 'expired'
  payload_json TEXT NOT NULL,   -- what the operator is being asked to judge
  requested_at TEXT DEFAULT (datetime('now')),
  decided_at   TEXT,
  decided_by   TEXT,
  note         TEXT,
  UNIQUE (task_id, stage)
);

CREATE INDEX IF NOT EXISTS idx_approvals_pending ON approvals (status, requested_at);
