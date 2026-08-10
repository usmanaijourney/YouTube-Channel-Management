"use client";

import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { useIntegrations } from "@/lib/hooks";

export default function IntegrationsPage() {
  const { data, error, isLoading } = useIntegrations();

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Every row here is a real check performed at request time (subprocess version check, live DB query, real
        OAuth token refresh, real trivial TTS synthesis) — never a fabricated status. Providers that are still
        mocked in the backend (WhatsApp, the topic/script LLM) report &quot;mocked&quot; rather than a fake
        &quot;healthy&quot;.
      </p>
      <Panel>
        {isLoading && <SkeletonRows rows={5} cols={5} />}
        {error && <ErrorState error={error} />}
        {data?.length === 0 && <EmptyState message="No integration data yet." />}
        {data && data.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <th className="pb-2 pr-4">Service</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Response time</th>
                  <th className="pb-2 pr-4">Error count</th>
                  <th className="pb-2 pr-4">Last check</th>
                  <th className="pb-2">Last error</th>
                </tr>
              </thead>
              <tbody>
                {data.map((svc) => (
                  <tr key={svc.service_name} className="border-b border-slate-900">
                    <td className="py-2.5 pr-4 font-mono text-xs text-slate-200">{svc.service_name}</td>
                    <td className="py-2.5 pr-4"><StatusBadge status={svc.status} /></td>
                    <td className="py-2.5 pr-4 text-slate-300">
                      {svc.response_time_ms !== null ? `${svc.response_time_ms}ms` : "—"}
                    </td>
                    <td className="py-2.5 pr-4 text-slate-300">{svc.error_count}</td>
                    <td className="py-2.5 pr-4 text-xs text-slate-500">
                      {svc.last_check_at ? new Date(svc.last_check_at).toLocaleString() : "—"}
                    </td>
                    <td className="py-2.5 max-w-xs truncate text-xs text-red-400" title={svc.last_error ?? undefined}>
                      {svc.last_error ?? "—"}
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
