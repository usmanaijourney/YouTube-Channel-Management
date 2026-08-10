import { AlertTriangle, Inbox, ShieldAlert, WifiOff } from "lucide-react";
import { ReactNode } from "react";
import { ApiError } from "@/lib/api";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-slate-800 ${className}`} />;
}

export function SkeletonRows({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-3">
          {Array.from({ length: cols }).map((__, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function EmptyState({ message = "No data yet." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-slate-500">
      <Inbox size={28} strokeWidth={1.5} />
      <p className="text-sm">{message}</p>
    </div>
  );
}

/** Renders a distinct "unauthorized" state for 401s (bad/missing BACKEND_API_KEY)
 * rather than lumping every failure into one generic error message. */
export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  const isUnauthorized = error instanceof ApiError && error.status === 401;

  if (isUnauthorized) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12 text-amber-400">
        <ShieldAlert size={28} strokeWidth={1.5} />
        <p className="text-sm">Unauthorized — check that BACKEND_API_KEY in frontend/.env.local matches the backend&apos;s key.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-red-400">
      <WifiOff size={28} strokeWidth={1.5} />
      <p className="text-sm">{error.message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 rounded border border-red-500/40 px-3 py-1 text-xs text-red-300 hover:bg-red-500/10"
        >
          Retry
        </button>
      )}
    </div>
  );
}

/** Honest "the backend doesn't support this yet" state — never fabricate data instead. */
export function UnavailableState({ reason, children }: { reason: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-slate-700 bg-slate-900/30 py-16 text-center text-slate-400">
      <AlertTriangle size={28} strokeWidth={1.5} className="text-slate-500" />
      <p className="max-w-md text-sm">{reason}</p>
      {children}
    </div>
  );
}
