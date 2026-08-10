"use client";

import Link from "next/link";
import { StatTile, Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { useAlerts, useAllAgents, useChannels, useIntegrations, useSystemHealth } from "@/lib/hooks";

export default function OverviewPage() {
  const health = useSystemHealth();
  const agents = useAllAgents();
  const channels = useChannels();
  const integrations = useIntegrations();
  const alerts = useAlerts();

  const healthyAgents = agents.data?.filter((a) => a.status === "idle" || a.status === "busy").length;

  return (
    <div className="space-y-6">
      {/* Status strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile
          label="Channels"
          value={
            health.data ? `${health.data.active_channels}/${health.data.total_channels}` : health.isLoading ? "…" : "—"
          }
          hint="active / total"
        />
        <StatTile
          label="Agents"
          value={agents.data ? `${healthyAgents}/${agents.data.length}` : agents.isLoading ? "…" : "—"}
          hint="healthy / total"
        />
        <StatTile
          label="Active Tasks"
          value={health.data?.tasks_in_progress ?? (health.isLoading ? "…" : "—")}
        />
        <StatTile
          label="Failed Tasks"
          value={health.data?.tasks_failed ?? (health.isLoading ? "…" : "—")}
        />
        <StatTile
          label="Videos (all-time)"
          value={
            channels.data ? channels.data.reduce((sum, c) => sum + c.videos_produced, 0) : channels.isLoading ? "…" : "—"
          }
          hint="no daily breakdown yet"
        />
        <StatTile
          label="Uploads (all-time)"
          value={
            channels.data ? channels.data.reduce((sum, c) => sum + c.videos_uploaded, 0) : channels.isLoading ? "…" : "—"
          }
          hint="no daily breakdown yet"
        />
      </div>
      <p className="text-xs text-slate-500">
        &quot;Today&quot; breakdowns aren&apos;t available — the backend doesn&apos;t expose date-filtered
        counts yet, so all-time totals are shown instead of inventing a daily figure.
      </p>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* System health */}
        <Panel title="System Health" action={<Link href="/integrations" className="text-xs text-sky-400 hover:underline">View all →</Link>}>
          {integrations.isLoading && <SkeletonRows rows={4} cols={3} />}
          {integrations.error && <ErrorState error={integrations.error} />}
          {integrations.data && (
            <ul className="divide-y divide-slate-800">
              {integrations.data.map((svc) => (
                <li key={svc.service_name} className="flex items-center justify-between py-2 text-sm">
                  <span className="font-mono text-slate-300">{svc.service_name}</span>
                  <div className="flex items-center gap-3">
                    {svc.response_time_ms !== null && (
                      <span className="text-xs text-slate-500">{svc.response_time_ms}ms</span>
                    )}
                    <StatusBadge status={svc.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        {/* Channel health */}
        <Panel title="Channel Health" action={<Link href="/channels" className="text-xs text-sky-400 hover:underline">View all →</Link>}>
          {channels.isLoading && <SkeletonRows rows={3} cols={4} />}
          {channels.error && <ErrorState error={channels.error} />}
          {channels.data?.length === 0 && <EmptyState message="No channels registered yet." />}
          {channels.data && channels.data.length > 0 && (
            <ul className="divide-y divide-slate-800">
              {channels.data.map((c) => (
                <li key={c.channel_id} className="flex items-center justify-between py-2 text-sm">
                  <Link href={`/channels/${c.channel_id}`} className="text-slate-200 hover:text-sky-400">
                    {c.name}
                  </Link>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span>{c.videos_uploaded} uploaded</span>
                    <StatusBadge status={c.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      {/* Recent alerts */}
      <Panel title="Recent Alerts" action={<Link href="/alerts" className="text-xs text-sky-400 hover:underline">View all →</Link>}>
        {alerts.isLoading && <SkeletonRows rows={3} cols={3} />}
        {alerts.error && <ErrorState error={alerts.error} />}
        {alerts.data?.length === 0 && <EmptyState message="No alerts. Everything's quiet." />}
        {alerts.data && alerts.data.length > 0 && (
          <ul className="divide-y divide-slate-800">
            {alerts.data.slice(0, 5).map((a) => (
              <li key={a.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <span className="text-slate-200">{a.event_type}</span>
                  {a.channel_id && <span className="ml-2 text-xs text-slate-500">{a.channel_id}</span>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{new Date(a.created_at).toLocaleString()}</span>
                  <StatusBadge status={a.severity} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
