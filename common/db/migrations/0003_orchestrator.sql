-- Master Orchestrator status (doc §19) — single row, upserted every health-aggregator cycle.
CREATE TABLE IF NOT EXISTS orchestrator_status (
  id                INTEGER PRIMARY KEY CHECK (id = 1),  -- enforces single-row table
  status            TEXT NOT NULL DEFAULT 'offline',      -- 'online' | 'offline'
  started_at        TEXT,
  last_cycle_at     TEXT,
  managed_channels  INTEGER DEFAULT 0,
  active_slots      INTEGER DEFAULT 0,
  max_slots         INTEGER DEFAULT 0,
  cycles_run        INTEGER DEFAULT 0
);
