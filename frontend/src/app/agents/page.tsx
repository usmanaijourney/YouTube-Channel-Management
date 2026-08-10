"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { useAllAgents } from "@/lib/hooks";

const STATUS_FILTERS = ["all", "healthy", "warning", "offline", "failed", "busy", "idle"] as const;

export default function AgentsPage() {
  const { data, error, isLoading } = useAllAgents();
  const [typeFilter, setTypeFilter] = useState("all");
  const [channelFilter, setChannelFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>("all");

  const types = useMemo(() => Array.from(new Set((data ?? []).map((a) => a.agent_type))), [data]);
  const channels = useMemo(() => Array.from(new Set((data ?? []).map((a) => a.channel_id))), [data]);

  const filtered = (data ?? [])
    .filter((a) => typeFilter === "all" || a.agent_type === typeFilter)
    .filter((a) => channelFilter === "all" || a.channel_id === channelFilter)
    .filter((a) => statusFilter === "all" || a.status === statusFilter);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1.5 text-sm text-slate-300">
          <option value="all">All types</option>
          {types.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select value={channelFilter} onChange={(e) => setChannelFilter(e.target.value)} className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1.5 text-sm text-slate-300">
          <option value="all">All channels</option>
          {channels.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)} className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1.5 text-sm text-slate-300">
          {STATUS_FILTERS.map((s) => (
            <option key={s} value={s}>{s === "all" ? "All statuses" : s}</option>
          ))}
        </select>
      </div>

      <Panel>
        {isLoading && <SkeletonRows rows={5} cols={7} />}
        {error && <ErrorState error={error} />}
        {data && filtered.length === 0 && <EmptyState message="No agents match your filters." />}
        {data && filtered.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <th className="pb-2 pr-4">Agent ID</th>
                  <th className="pb-2 pr-4">Type</th>
                  <th className="pb-2 pr-4">Channel</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Last heartbeat</th>
                  <th className="pb-2 pr-4">Failures</th>
                  <th className="pb-2">Avg duration</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => (
                  <tr key={a.agent_id} className="border-b border-slate-900 hover:bg-slate-900/40">
                    <td className="py-2.5 pr-4">
                      <Link href={`/channels/${a.channel_id}/agents/${a.agent_type}`} className="font-mono text-xs text-slate-300 hover:text-sky-400">
                        {a.agent_id}
                      </Link>
                    </td>
                    <td className="py-2.5 pr-4 text-slate-300">{a.agent_type}</td>
                    <td className="py-2.5 pr-4 text-slate-400">{a.channel_name}</td>
                    <td className="py-2.5 pr-4"><StatusBadge status={a.status} /></td>
                    <td className="py-2.5 pr-4 text-xs text-slate-500">
                      {a.last_heartbeat ? new Date(a.last_heartbeat).toLocaleString() : "never"}
                    </td>
                    <td className="py-2.5 pr-4 text-slate-300">{a.failure_count}</td>
                    <td className="py-2.5 text-slate-300">{a.avg_exec_ms ? `${a.avg_exec_ms}ms` : "—"}</td>
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
