"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { CheckCircle2, XCircle } from "lucide-react";
import { Panel, StatTile } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { useTaskDetail } from "@/lib/hooks";

export default function TaskDetailPage() {
  const { channelId, taskId } = useParams<{ channelId: string; taskId: string }>();
  const { data, error, isLoading } = useTaskDetail(channelId, taskId);

  if (isLoading) return <SkeletonRows rows={6} cols={4} />;
  if (error) return <ErrorState error={error} />;
  if (!data) return <EmptyState message="Task not found." />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="font-mono text-lg font-semibold text-slate-100">{data.task_id}</h2>
            <StatusBadge status={data.state} />
          </div>
          <div className="mt-1 text-sm text-slate-500">
            Channel: <Link href={`/channels/${channelId}`} className="text-sky-400 hover:underline">{channelId}</Link>
            {data.topic && <span className="ml-3">Topic: {data.topic}</span>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Created" value={new Date(data.created_at).toLocaleString()} />
        <StatTile label="Updated" value={new Date(data.updated_at).toLocaleString()} />
        <StatTile label="Transitions" value={data.events.length} />
        <StatTile label="State" value={<StatusBadge status={data.state} />} />
      </div>

      <Panel title="Timeline">
        {data.events.length === 0 ? (
          <EmptyState message="No events recorded." />
        ) : (
          <ol className="space-y-3">
            {data.events.map((e) => (
              <li key={e.id} className="flex gap-3 border-b border-slate-900 pb-3 last:border-0">
                {e.to_state === "FAILED" ? (
                  <XCircle size={16} className="mt-0.5 shrink-0 text-red-400" />
                ) : (
                  <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-400" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-200">
                      {e.from_state ?? "∅"} → <span className="font-medium">{e.to_state}</span>
                    </span>
                    <span className="text-xs text-slate-500">{new Date(e.created_at).toLocaleString()}</span>
                  </div>
                  {e.agent_id && <div className="mt-0.5 font-mono text-xs text-slate-500">agent: {e.agent_id}</div>}
                  {e.error && (
                    <pre className="mt-1 overflow-x-auto rounded bg-red-500/5 p-2 text-xs text-red-300">
                      {JSON.stringify(e.error, null, 2)}
                    </pre>
                  )}
                  {e.payload && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-300">payload</summary>
                      <pre className="mt-1 overflow-x-auto rounded bg-slate-950 p-2 text-xs text-slate-400">
                        {JSON.stringify(e.payload, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </Panel>

      <Panel title="Dependency Tree">
        <p className="text-sm text-slate-500">
          Not available — this system doesn&apos;t model scene-level sub-tasks or a parent/child task graph;
          each task is a single linear pipeline run (see Timeline above for its stage-by-stage history).
        </p>
      </Panel>
    </div>
  );
}
