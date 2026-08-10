"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { LayoutGrid, List, Search } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { useChannels } from "@/lib/hooks";

type SortKey = "name" | "status" | "videos_uploaded" | "cost_total";

export default function ChannelsPage() {
  const { data, error, isLoading } = useChannels();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [view, setView] = useState<"table" | "grid">("table");

  const filtered = useMemo(() => {
    if (!data) return [];
    return data
      .filter((c) => c.name.toLowerCase().includes(query.toLowerCase()) || c.channel_id.includes(query))
      .filter((c) => statusFilter === "all" || c.status === statusFilter)
      .sort((a, b) => {
        if (sortKey === "name") return a.name.localeCompare(b.name);
        if (sortKey === "status") return a.status.localeCompare(b.status);
        return (b[sortKey] as number) - (a[sortKey] as number);
      });
  }, [data, query, statusFilter, sortKey]);

  const statuses = useMemo(() => Array.from(new Set((data ?? []).map((c) => c.status))), [data]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search size={14} className="pointer-events-none absolute left-2.5 top-2.5 text-slate-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search channels…"
            className="w-56 rounded-md border border-slate-800 bg-slate-900 py-1.5 pl-8 pr-3 text-sm text-slate-200 placeholder:text-slate-600 focus:border-sky-600 focus:outline-none"
          />
        </div>
        <select
          aria-label="Filter by status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1.5 text-sm text-slate-300 focus:border-sky-600 focus:outline-none"
        >
          <option value="all">All statuses</option>
          {statuses.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          aria-label="Sort channels by"
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as SortKey)}
          className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1.5 text-sm text-slate-300 focus:border-sky-600 focus:outline-none"
        >
          <option value="name">Sort: Name</option>
          <option value="status">Sort: Status</option>
          <option value="videos_uploaded">Sort: Videos uploaded</option>
          <option value="cost_total">Sort: Cost</option>
        </select>
        <div className="ml-auto flex rounded-md border border-slate-800">
          <button
            onClick={() => setView("table")}
            className={`p-1.5 ${view === "table" ? "bg-sky-500/10 text-sky-400" : "text-slate-500"}`}
            title="Table view"
          >
            <List size={16} />
          </button>
          <button
            onClick={() => setView("grid")}
            className={`p-1.5 ${view === "grid" ? "bg-sky-500/10 text-sky-400" : "text-slate-500"}`}
            title="Grid view"
          >
            <LayoutGrid size={16} />
          </button>
        </div>
      </div>

      <Panel>
        {isLoading && <SkeletonRows rows={4} cols={6} />}
        {error && <ErrorState error={error} />}
        {data && filtered.length === 0 && <EmptyState message="No channels match your filters." />}

        {data && filtered.length > 0 && view === "table" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <th className="pb-2 pr-4">Channel</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Current tasks</th>
                  <th className="pb-2 pr-4">Videos uploaded</th>
                  <th className="pb-2 pr-4">Cost</th>
                  <th className="pb-2">Last activity</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.channel_id} className="border-b border-slate-900 hover:bg-slate-900/40">
                    <td className="py-2.5 pr-4">
                      <Link href={`/channels/${c.channel_id}`} className="text-slate-200 hover:text-sky-400">
                        {c.name}
                      </Link>
                      <div className="text-xs text-slate-500">{c.niche}</div>
                    </td>
                    <td className="py-2.5 pr-4">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="py-2.5 pr-4 text-slate-300">{c.current_task_count}</td>
                    <td className="py-2.5 pr-4 text-slate-300">
                      {c.videos_uploaded} / {c.videos_produced}
                    </td>
                    <td className="py-2.5 pr-4 text-slate-300">${c.cost_total.toFixed(4)}</td>
                    <td className="py-2.5 text-xs text-slate-500">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && filtered.length > 0 && view === "grid" && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((c) => (
              <Link
                key={c.channel_id}
                href={`/channels/${c.channel_id}`}
                className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 hover:border-sky-700"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-100">{c.name}</span>
                  <StatusBadge status={c.status} />
                </div>
                <div className="mt-1 text-xs text-slate-500">{c.niche}</div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-400">
                  <div>Tasks: {c.current_task_count}</div>
                  <div>Uploaded: {c.videos_uploaded}</div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
