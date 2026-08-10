"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useSWRConfig } from "swr";
import { RefreshCw, UserCircle } from "lucide-react";
import { NAV_ITEMS } from "./nav";

function currentPageLabel(pathname: string): string {
  const match = NAV_ITEMS.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  return match?.label ?? "Dashboard";
}

export function TopBar() {
  const pathname = usePathname();
  const { mutate } = useSWRConfig();
  // Starts null so server and first client render match exactly; the real
  // Date is only known client-side, so setting it must happen post-mount —
  // this is the sanctioned exception to "don't setState in an effect"
  // (synchronizing with a value the server can't produce identically).
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only mount sync, avoids SSR/client Date hydration mismatch
    setLastRefreshed(new Date());
  }, []);

  const segments = pathname.split("/").filter(Boolean);
  const pageLabel = currentPageLabel(pathname);

  async function handleRefresh() {
    setRefreshing(true);
    await mutate(() => true);
    setLastRefreshed(new Date());
    setRefreshing(false);
  }

  return (
    <header className="flex items-center justify-between border-b border-slate-800 bg-slate-950/80 px-6 py-3 backdrop-blur">
      <div>
        <div className="text-xs text-slate-500">
          MASTER CONTROL{segments.length > 0 && " / "}
          {segments.map((s) => s.replace(/-/g, " ")).join(" / ")}
        </div>
        <h1 className="text-lg font-semibold text-slate-100">{pageLabel}</h1>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Live
          {lastRefreshed && <span className="ml-1">· updated {lastRefreshed.toLocaleTimeString()}</span>}
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-1.5 rounded-md border border-slate-800 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-900"
        >
          <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
          Refresh
        </button>
        <UserCircle size={22} className="text-slate-500" />
      </div>
    </header>
  );
}
