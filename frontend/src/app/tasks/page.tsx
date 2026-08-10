"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { useAllTasks } from "@/lib/hooks";

export default function TasksPage() {
  const { data, error, isLoading } = useAllTasks();
  const [query, setQuery] = useState("");
  const [stateFilter, setStateFilter] = useState("all");

  const states = useMemo(() => Array.from(new Set((data ?? []).map((t) => t.state))), [data]);

  const filtered = (data ?? [])
    .filter((t) => t.task_id.includes(query) || (t.topic ?? "").toLowerCase().includes(query.toLowerCase()))
    .filter((t) => stateFilter === "all" || t.state === stateFilter)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Aggregated from each channel&apos;s 20 most recent tasks — there&apos;s no global, paginated task-list
        endpoint yet, so very old or high-volume tasks may not appear here.
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search task ID or topic…"
          className="w-64 rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-600 focus:border-sky-600 focus:outline-none"
        />
        <select value={stateFilter} onChange={(e) => setStateFilter(e.target.value)} className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1.5 text-sm text-slate-300">
          <option value="all">All states</option>
          {states.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <Panel>
        {isLoading && <SkeletonRows rows={6} cols={5} />}
        {error && <ErrorState error={error} />}
        {data && filtered.length === 0 && <EmptyState message="No tasks match your filters." />}
        {data && filtered.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <th className="pb-2 pr-4">Task ID</th>
                  <th className="pb-2 pr-4">Channel</th>
                  <th className="pb-2 pr-4">Topic</th>
                  <th className="pb-2 pr-4">State</th>
                  <th className="pb-2 pr-4">Created</th>
                  <th className="pb-2">Updated</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr key={t.task_id} className="border-b border-slate-900 hover:bg-slate-900/40">
                    <td className="py-2.5 pr-4">
                      <Link href={`/channels/${t.channel_id}/tasks/${t.task_id}`} className="font-mono text-xs text-slate-300 hover:text-sky-400">
                        {t.task_id}
                      </Link>
                    </td>
                    <td className="py-2.5 pr-4 text-slate-400">{t.channel_name}</td>
                    <td className="py-2.5 pr-4 text-slate-400">{t.topic ?? "—"}</td>
                    <td className="py-2.5 pr-4"><StatusBadge status={t.state} /></td>
                    <td className="py-2.5 pr-4 text-xs text-slate-500">{new Date(t.created_at).toLocaleString()}</td>
                    <td className="py-2.5 text-xs text-slate-500">{new Date(t.updated_at).toLocaleString()}</td>
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
