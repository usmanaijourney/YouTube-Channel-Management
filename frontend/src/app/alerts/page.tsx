"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { useAlerts } from "@/lib/hooks";

const SEVERITIES = ["all", "critical", "warning", "info"] as const;
const ACTIONS = ["Acknowledge", "Resolve", "Mute"];

export default function AlertsPage() {
  const [severity, setSeverity] = useState<(typeof SEVERITIES)[number]>("all");
  const { data, error, isLoading } = useAlerts(severity === "all" ? undefined : severity);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {SEVERITIES.map((s) => (
          <button
            key={s}
            onClick={() => setSeverity(s)}
            className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
              severity === s
                ? "border-sky-600 bg-sky-500/10 text-sky-300"
                : "border-slate-800 text-slate-400 hover:bg-slate-900"
            }`}
          >
            {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <Panel>
        {isLoading && <SkeletonRows rows={5} cols={5} />}
        {error && <ErrorState error={error} />}
        {data?.length === 0 && <EmptyState message="No alerts." />}
        {data && data.length > 0 && (
          <ul className="divide-y divide-slate-800">
            {data.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={a.severity} />
                    <span className="text-sm text-slate-200">{a.event_type}</span>
                    {a.channel_id && <span className="text-xs text-slate-500">· {a.channel_id}</span>}
                  </div>
                  {a.payload && (
                    <pre className="mt-1 overflow-x-auto rounded bg-slate-950 p-2 text-xs text-slate-400">
                      {JSON.stringify(a.payload, null, 2)}
                    </pre>
                  )}
                  <div className="mt-1 text-xs text-slate-500">{new Date(a.created_at).toLocaleString()}</div>
                </div>
                <div className="flex shrink-0 gap-1.5">
                  {ACTIONS.map((action) => (
                    <button
                      key={action}
                      disabled
                      title="Not available — no write endpoints exist on the backend yet"
                      className="cursor-not-allowed rounded border border-slate-800 px-2 py-1 text-xs text-slate-600"
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
