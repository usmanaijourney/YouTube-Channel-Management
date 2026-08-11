"use client";

import { useState } from "react";
import { mutate } from "swr";

import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/ui/States";
import { api, ApiError } from "@/lib/api";
import { useApprovals } from "@/lib/hooks";
import type { Approval } from "@/lib/types";

const STAGE_LABELS: Record<string, string> = {
  topic: "Topic",
  script: "Script",
  pre_upload: "Pre-upload",
};

function ApprovalCard({ approval }: { approval: Approval }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approved" | "rejected" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: "approved" | "rejected") {
    setBusy(decision);
    setError(null);
    try {
      await api.decideApproval(approval.task_id, approval.stage, decision, note);
      // Revalidate both lists: deciding a gate changes the pending set and
      // writes an audit entry.
      await Promise.all([
        mutate((key) => Array.isArray(key) && key[0] === "approvals"),
        mutate("audit-logs"),
      ]);
    } catch (e) {
      // A 409 means someone (or the run's own timeout) already settled this.
      // Refresh rather than leave a stale card offering a decision that can't land.
      setError(e instanceof ApiError ? e.message : "Could not submit the decision");
      if (e instanceof ApiError && e.status === 409) {
        await mutate((key) => Array.isArray(key) && key[0] === "approvals");
      }
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-slate-100">
          {STAGE_LABELS[approval.stage] ?? approval.stage}
        </span>
        <StatusBadge status={approval.status} />
        <span className="text-xs text-slate-500">
          {approval.channel_id} · {approval.task_id}
        </span>
        <span className="ml-auto text-xs text-slate-500">
          asked {new Date(approval.requested_at + "Z").toLocaleString()}
        </span>
      </div>

      <pre className="mt-3 max-h-64 overflow-auto rounded border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-300">
        {JSON.stringify(approval.payload, null, 2)}
      </pre>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Optional note (recorded in the audit log)"
          className="min-w-0 flex-1 rounded border border-slate-800 bg-slate-950/60 px-3 py-1.5 text-sm text-slate-200 placeholder:text-slate-600 focus:border-slate-600 focus:outline-none"
        />
        <button
          onClick={() => decide("approved")}
          disabled={busy !== null}
          className="rounded border border-emerald-500/30 bg-emerald-500/15 px-3 py-1.5 text-sm font-medium text-emerald-400 hover:bg-emerald-500/25 disabled:opacity-50"
        >
          {busy === "approved" ? "Approving…" : "Approve"}
        </button>
        <button
          onClick={() => decide("rejected")}
          disabled={busy !== null}
          className="rounded border border-red-500/30 bg-red-500/15 px-3 py-1.5 text-sm font-medium text-red-400 hover:bg-red-500/25 disabled:opacity-50"
        >
          {busy === "rejected" ? "Rejecting…" : "Reject"}
        </button>
      </div>

      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </div>
  );
}

export default function ApprovalsPage() {
  const pending = useApprovals("pending");
  const all = useApprovals();

  const decided = all.data?.filter((a) => a.status !== "pending") ?? [];

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        A run blocks here until you decide. Gates left unanswered for six hours expire on their own, so a
        forgotten task fails visibly instead of holding a production slot indefinitely.
      </p>

      <Panel title="Waiting on you">
        {pending.isLoading && <SkeletonRows rows={2} cols={3} />}
        {pending.error && <ErrorState error={pending.error} />}
        {pending.data?.length === 0 && <EmptyState message="Nothing waiting. No run is blocked." />}
        {pending.data && pending.data.length > 0 && (
          <div className="space-y-3">
            {pending.data.map((a) => (
              <ApprovalCard key={a.id} approval={a} />
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Decided">
        {all.isLoading && <SkeletonRows rows={3} cols={4} />}
        {all.error && <ErrorState error={all.error} />}
        {!all.isLoading && decided.length === 0 && <EmptyState message="No decisions recorded yet." />}
        {decided.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                  <th className="pb-2 pr-4">Stage</th>
                  <th className="pb-2 pr-4">Task</th>
                  <th className="pb-2 pr-4">Outcome</th>
                  <th className="pb-2 pr-4">Decided</th>
                  <th className="pb-2">Note</th>
                </tr>
              </thead>
              <tbody>
                {decided.map((a) => (
                  <tr key={a.id} className="border-b border-slate-900">
                    <td className="py-2.5 pr-4 text-slate-200">{STAGE_LABELS[a.stage] ?? a.stage}</td>
                    <td className="py-2.5 pr-4 font-mono text-xs text-slate-400">{a.task_id}</td>
                    <td className="py-2.5 pr-4">
                      <StatusBadge status={a.status} />
                    </td>
                    <td className="py-2.5 pr-4 text-xs text-slate-500">
                      {a.decided_at ? new Date(a.decided_at + "Z").toLocaleString() : "—"}
                    </td>
                    <td className="py-2.5 text-xs text-slate-400">{a.note ?? "—"}</td>
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
