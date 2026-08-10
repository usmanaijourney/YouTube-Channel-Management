"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Panel, StatTile } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { useAgentDetail } from "@/lib/hooks";

const CONTROLS = ["Retry", "Restart", "Pause", "Resume", "Clear queue"];

export default function AgentDetailPage() {
  const { channelId, agentType } = useParams<{ channelId: string; agentType: string }>();
  const { data, error, isLoading } = useAgentDetail(channelId, agentType);

  if (isLoading) return <SkeletonRows rows={5} cols={4} />;
  if (error) return <ErrorState error={error} />;
  if (!data) return <EmptyState message="Agent not found." />;

  const totalFailures = data.instances.reduce((sum, i) => sum + i.failure_count, 0);
  const totalRetries = data.instances.reduce((sum, i) => sum + i.retry_count, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">{data.agent_type}</h2>
          <div className="mt-1 text-sm text-slate-500">
            Channel: <Link href={`/channels/${channelId}`} className="text-sky-400 hover:underline">{channelId}</Link>
          </div>
        </div>
        <div className="flex gap-2">
          {CONTROLS.map((c) => (
            <button
              key={c}
              disabled
              title="Not available — no action endpoints exist on the backend yet"
              className="cursor-not-allowed rounded-md border border-slate-800 px-2.5 py-1.5 text-xs text-slate-600"
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Instances" value={data.instances.length} />
        <StatTile label="Total failures" value={totalFailures} />
        <StatTile label="Total retries" value={totalRetries} />
        <StatTile label="Recent events" value={data.recent_events.length} />
      </div>

      <Panel title="Instances">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                <th className="pb-2 pr-4">Agent ID</th>
                <th className="pb-2 pr-4">Status</th>
                <th className="pb-2 pr-4">Last heartbeat</th>
                <th className="pb-2 pr-4">Last success</th>
                <th className="pb-2 pr-4">Last failure</th>
                <th className="pb-2">Avg duration</th>
              </tr>
            </thead>
            <tbody>
              {data.instances.map((i) => (
                <tr key={i.agent_id} className="border-b border-slate-900">
                  <td className="py-2.5 pr-4 font-mono text-xs text-slate-300">{i.agent_id}</td>
                  <td className="py-2.5 pr-4"><StatusBadge status={i.status} /></td>
                  <td className="py-2.5 pr-4 text-xs text-slate-500">{i.last_heartbeat ? new Date(i.last_heartbeat).toLocaleString() : "—"}</td>
                  <td className="py-2.5 pr-4 text-xs text-slate-500">{i.last_success ? new Date(i.last_success).toLocaleString() : "—"}</td>
                  <td className="py-2.5 pr-4 text-xs text-slate-500">{i.last_failure ? new Date(i.last_failure).toLocaleString() : "—"}</td>
                  <td className="py-2.5 text-slate-300">{i.avg_exec_ms ? `${i.avg_exec_ms}ms` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Recent Events (Logs)">
        {data.recent_events.length === 0 ? (
          <EmptyState message="No recent events for this agent." />
        ) : (
          <ul className="space-y-2">
            {data.recent_events.map((e) => (
              <li key={e.id} className="flex items-center justify-between rounded border border-slate-800 px-3 py-2 text-sm">
                <div>
                  <Link href={`/channels/${channelId}/tasks/${e.task_id}`} className="font-mono text-xs text-slate-300 hover:text-sky-400">
                    {e.task_id}
                  </Link>
                  <span className="ml-2 text-slate-400">
                    {e.from_state ?? "∅"} → {e.to_state}
                  </span>
                </div>
                <span className="text-xs text-slate-500">{new Date(e.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
