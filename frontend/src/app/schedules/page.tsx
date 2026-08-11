"use client";

import { useState } from "react";
import { mutate } from "swr";

import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { api, ApiError } from "@/lib/api";
import { useSchedules } from "@/lib/hooks";

function ScheduleToggle({ channelId, enabled }: { channelId: string; enabled: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    setBusy(true);
    setError(null);
    try {
      await api.setScheduleEnabled(channelId, !enabled);
      await Promise.all([mutate("schedules"), mutate("audit-logs")]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not update the schedule");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <button
        onClick={toggle}
        disabled={busy}
        className="rounded border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-xs font-medium text-slate-200 hover:bg-slate-700/60 disabled:opacity-50"
      >
        {busy ? "Saving…" : enabled ? "Pause" : "Resume"}
      </button>
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}

export default function SchedulesPage() {
  const { data, error, isLoading } = useSchedules();

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Schedule configuration and last-run state are real, and pausing genuinely blocks a run — `run.py`
        refuses to start a paused channel. No automatic scheduler daemon runs these yet, so each row
        reflects the last manually-triggered execution, not a live cron.
      </p>
      <Panel>
        {isLoading && <SkeletonRows rows={3} cols={4} />}
        {error && <ErrorState error={error} />}
        {data?.length === 0 && <EmptyState message="No schedules configured." />}
        {data && data.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <th className="pb-2 pr-4">Channel</th>
                  <th className="pb-2 pr-4">Enabled</th>
                  <th className="pb-2 pr-4">Preferred hours (UTC)</th>
                  <th className="pb-2 pr-4">Last run</th>
                  <th className="pb-2 pr-4">Last status</th>
                  <th className="pb-2 pr-4">Next run (estimate)</th>
                  <th className="pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.map((s) => (
                  <tr key={s.channel_id} className="border-b border-slate-900">
                    <td className="py-2.5 pr-4 text-slate-200">{s.channel_id}</td>
                    <td className="py-2.5 pr-4">
                      <StatusBadge status={s.enabled ? "healthy" : "paused"} />
                    </td>
                    <td className="py-2.5 pr-4 text-slate-300">{s.preferred_hours_utc.join(", ")}</td>
                    <td className="py-2.5 pr-4 text-xs text-slate-500">
                      {s.last_run_at ? new Date(s.last_run_at).toLocaleString() : "never"}
                    </td>
                    <td className="py-2.5 pr-4">
                      <StatusBadge status={s.last_run_status} />
                    </td>
                    <td className="py-2.5 pr-4 text-xs text-slate-500">
                      {s.next_run_estimate ? new Date(s.next_run_estimate).toLocaleString() : "—"}
                    </td>
                    <td className="py-2.5">
                      <ScheduleToggle channelId={s.channel_id} enabled={s.enabled} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
