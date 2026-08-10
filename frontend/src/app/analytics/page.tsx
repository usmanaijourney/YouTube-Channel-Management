"use client";

import { Panel, StatTile } from "@/components/ui/Panel";
import { ErrorState, SkeletonRows, UnavailableState } from "@/components/ui/States";
import { useChannels, useSystemHealth } from "@/lib/hooks";

export default function AnalyticsPage() {
  const health = useSystemHealth();
  const channels = useChannels();

  const successRate =
    health.data && health.data.total_tasks > 0
      ? ((health.data.tasks_completed / health.data.total_tasks) * 100).toFixed(1)
      : null;

  return (
    <div className="space-y-6">
      <Panel title="What's real today">
        {health.isLoading && <SkeletonRows rows={2} cols={4} />}
        {health.error && <ErrorState error={health.error} />}
        {health.data && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Total cost" value={`$${health.data.cost_total.toFixed(4)}`} />
            <StatTile label="Task success rate" value={successRate ? `${successRate}%` : "—"} />
            <StatTile label="Tasks completed" value={health.data.tasks_completed} />
            <StatTile label="Tasks failed" value={health.data.tasks_failed} />
          </div>
        )}
      </Panel>

      <Panel title="Per-channel cost & output">
        {channels.isLoading && <SkeletonRows rows={3} cols={4} />}
        {channels.error && <ErrorState error={channels.error} />}
        {channels.data && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <th className="pb-2 pr-4">Channel</th>
                  <th className="pb-2 pr-4">Videos produced</th>
                  <th className="pb-2 pr-4">Videos uploaded</th>
                  <th className="pb-2">Cost</th>
                </tr>
              </thead>
              <tbody>
                {channels.data.map((c) => (
                  <tr key={c.channel_id} className="border-b border-slate-900">
                    <td className="py-2.5 pr-4 text-slate-200">{c.name}</td>
                    <td className="py-2.5 pr-4 text-slate-300">{c.videos_produced}</td>
                    <td className="py-2.5 pr-4 text-slate-300">{c.videos_uploaded}</td>
                    <td className="py-2.5 text-slate-300">${c.cost_total.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="YouTube performance metrics">
        <UnavailableState reason="Views, watch time, subscribers, CTR, and retention require the YouTube Analytics API (a different API/OAuth scope than the Data API v3 upload access already wired). Not integrated yet — showing fabricated numbers here would violate this platform's own 'no fake metrics' rule." />
      </Panel>
    </div>
  );
}
