"use client";

import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { useSchedules } from "@/lib/hooks";

export default function SchedulesPage() {
  const { data, error, isLoading } = useSchedules();

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Schedule configuration and last-run state are real. No automatic scheduler daemon runs these yet —
        each row reflects the last manually-triggered `run.py` execution, not a live cron.
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
                  <th className="pb-2">Next run (estimate)</th>
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
                    <td className="py-2.5 text-xs text-slate-500">
                      {s.next_run_estimate ? new Date(s.next_run_estimate).toLocaleString() : "—"}
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
