"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Panel, StatTile } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows, UnavailableState } from "@/components/ui/States";
import { PipelineVisualization } from "@/components/PipelineVisualization";
import { useAlerts, useChannelDetail, useTaskDetail } from "@/lib/hooks";

export default function ChannelDetailPage() {
  const { channelId } = useParams<{ channelId: string }>();
  const { data: channel, error, isLoading } = useChannelDetail(channelId);
  const { data: allAlerts } = useAlerts();

  const mostRecentTaskId = channel?.recent_tasks[0]?.task_id;
  const { data: mostRecentTask } = useTaskDetail(channelId, mostRecentTaskId);

  const channelAlerts = allAlerts?.filter((a) => a.channel_id === channelId) ?? [];

  if (isLoading) return <SkeletonRows rows={6} cols={4} />;
  if (error) return <ErrorState error={error} />;
  if (!channel) return <EmptyState message="Channel not found." />;

  const failedFromState =
    mostRecentTask?.state === "FAILED"
      ? mostRecentTask.events.find((e) => e.to_state === "FAILED")?.from_state
      : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold text-slate-100">{channel.name}</h2>
            <StatusBadge status={channel.status} />
          </div>
          <div className="mt-1 text-sm text-slate-500">
            {channel.channel_id} · {channel.niche}
          </div>
        </div>
        <Link href="/channels" className="text-sm text-sky-400 hover:underline">
          ← All channels
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        <StatTile label="Current tasks" value={channel.current_task_count} />
        <StatTile label="Completed" value={channel.tasks_completed} />
        <StatTile label="Failed" value={channel.tasks_failed} />
        <StatTile label="Videos produced" value={channel.videos_produced} />
        <StatTile label="Videos uploaded" value={channel.videos_uploaded} />
        <StatTile label="Cost" value={`$${channel.cost_total.toFixed(4)}`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Agent Team">
          {channel.agents.length === 0 ? (
            <EmptyState message="No agents have run for this channel yet." />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {channel.agents.map((a) => (
                <Link
                  key={a.agent_id}
                  href={`/channels/${channelId}/agents/${a.agent_type}`}
                  className="rounded-md border border-slate-800 p-3 hover:border-sky-700"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-slate-300">{a.agent_type}</span>
                    <StatusBadge status={a.status} />
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-slate-500">
                    <span>Failures: {a.failure_count}</span>
                    <span>Retries: {a.retry_count}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Production Pipeline" action={mostRecentTaskId && <span className="text-xs text-slate-500">task {mostRecentTaskId}</span>}>
          {mostRecentTaskId && mostRecentTask ? (
            <PipelineVisualization currentState={mostRecentTask.state} failedFromState={failedFromState} />
          ) : (
            <EmptyState message="No tasks have run for this channel yet." />
          )}
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Recent Tasks">
          {channel.recent_tasks.length === 0 ? (
            <EmptyState message="No tasks yet." />
          ) : (
            <ul className="divide-y divide-slate-800">
              {channel.recent_tasks.map((t) => (
                <li key={t.task_id} className="flex items-center justify-between py-2 text-sm">
                  <Link href={`/channels/${channelId}/tasks/${t.task_id}`} className="font-mono text-xs text-slate-300 hover:text-sky-400">
                    {t.task_id}
                  </Link>
                  <StatusBadge status={t.state} />
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Channel Alerts">
          {channelAlerts.length === 0 ? (
            <EmptyState message="No alerts for this channel." />
          ) : (
            <ul className="divide-y divide-slate-800">
              {channelAlerts.map((a) => (
                <li key={a.id} className="flex items-center justify-between py-2 text-sm">
                  <span className="text-slate-200">{a.event_type}</span>
                  <StatusBadge status={a.severity} />
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <Panel title="Recent Videos">
        <UnavailableState reason="No video-listing endpoint exists yet — only aggregate counts (produced/uploaded, shown above). Add GET /api/channels/{id}/videos to the backend to support this." />
      </Panel>
    </div>
  );
}
