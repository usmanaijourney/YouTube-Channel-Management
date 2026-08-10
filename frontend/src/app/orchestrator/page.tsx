"use client";

import { Panel, StatTile } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows, UnavailableState } from "@/components/ui/States";
import { useOrchestrator, useSystemHealth } from "@/lib/hooks";

function formatUptime(startedAt: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(startedAt).getTime()) / 1000);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export default function OrchestratorPage() {
  const { data, error, isLoading } = useOrchestrator();
  const health = useSystemHealth();

  if (isLoading) return <SkeletonRows rows={5} cols={4} />;
  if (error) return <ErrorState error={error} />;

  if (!data?.status) {
    return (
      <UnavailableState reason="The Master Orchestrator service exists (master_orchestrator/app.py) but hasn't run a health-aggregator cycle yet — it's either not running, or hasn't completed its first 30s cycle.">
        <code className="rounded bg-slate-900 px-2 py-1 text-xs text-slate-300">
          uvicorn master_orchestrator.app:app --port 8100
        </code>
      </UnavailableState>
    );
  }

  const s = data.status;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <StatusBadge status={s.status} />
        <span className="text-sm text-slate-500">
          {s.started_at && `up ${formatUptime(s.started_at)}`}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Managed channels" value={s.managed_channels} />
        <StatTile label="Production slots" value={`${s.active_slots} / ${s.max_slots}`} hint="active / max" />
        <StatTile label="Health cycles run" value={s.cycles_run} />
        <StatTile
          label="Last cycle"
          value={s.last_cycle_at ? new Date(s.last_cycle_at).toLocaleTimeString() : "—"}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Active tasks (global)" value={health.data?.tasks_in_progress ?? "…"} />
        <StatTile label="Failed tasks (global)" value={health.data?.tasks_failed ?? "…"} />
      </div>
      <p className="text-xs text-slate-500">
        CPU/memory and &quot;current objectives&quot; aren&apos;t tracked — this is a single lightweight Python
        process, and there&apos;s no strategic-planning LLM loop wired up yet (doc §19&apos;s
        <code className="mx-1 rounded bg-slate-900 px-1">strategic_review_weekly</code>
        is design-only).
      </p>

      <Panel title="Recent Decisions / Alerts">
        {data.recent_events.length === 0 ? (
          <EmptyState message="No orchestrator-raised alerts yet." />
        ) : (
          <ul className="divide-y divide-slate-800">
            {data.recent_events.map((e) => (
              <li key={e.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <span className="text-slate-200">{e.event_type}</span>
                  {e.channel_id && <span className="ml-2 text-xs text-slate-500">{e.channel_id}</span>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{new Date(e.created_at).toLocaleString()}</span>
                  <StatusBadge status={e.severity} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
