const STATUS_COLOR: Record<string, string> = {
  // green — healthy / completed
  healthy: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  completed: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  closed: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  active: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  uploaded: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  idle: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",

  // blue — in progress
  running: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  busy: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  in_progress: "bg-sky-500/15 text-sky-400 border-sky-500/30",

  // amber — warning / queued / pending
  warning: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  queued: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  pending: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  degraded: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  paused: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  mocked: "bg-amber-500/15 text-amber-400 border-amber-500/30",

  // red — failed / critical
  failed: "bg-red-500/15 text-red-400 border-red-500/30",
  error: "bg-red-500/15 text-red-400 border-red-500/30",
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
  timeout: "bg-red-500/15 text-red-400 border-red-500/30",
  cancelled: "bg-red-500/15 text-red-400 border-red-500/30",
};

const FALLBACK = "bg-slate-500/15 text-slate-400 border-slate-500/30"; // gray — inactive/unknown

export function StatusBadge({ status }: { status: string | null | undefined }) {
  const key = (status ?? "unknown").toLowerCase();
  const classes = STATUS_COLOR[key] ?? FALLBACK;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${classes}`}
    >
      {status ?? "unknown"}
    </span>
  );
}
