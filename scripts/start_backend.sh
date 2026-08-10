#!/usr/bin/env bash
# Boots both backend services in one container.
#
# They are co-located deliberately: they share a single SQLite file, and a
# Railway volume attaches to exactly one service. The dashboard API takes the
# public $PORT; the orchestrator stays on an internal port, reachable from the
# same container and over the private network.
set -euo pipefail

: "${PORT:=8000}"
: "${ORCHESTRATOR_PORT:=8100}"
# Binding :: is not a safe default: whether a v6 socket also accepts IPv4
# depends on the container's bindv6only setting, and both Railway's edge proxy
# and its private DNS hand out IPv4. Overridable in case a platform needs v6.
: "${BIND_HOST:=0.0.0.0}"

python -m uvicorn master_orchestrator.app:app --host "$BIND_HOST" --port "$ORCHESTRATOR_PORT" &
orchestrator_pid=$!

python -m uvicorn dashboard.api.app:app --host "$BIND_HOST" --port "$PORT" &
dashboard_pid=$!

# Exit as soon as either process does, so the platform restarts the whole
# container. Otherwise a dead orchestrator leaves a healthy-looking dashboard
# serving stale slot/health data indefinitely.
wait -n
exit_code=$?
kill -TERM "$orchestrator_pid" "$dashboard_pid" 2>/dev/null || true
exit "$exit_code"
