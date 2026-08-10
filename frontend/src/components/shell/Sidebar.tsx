"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ChevronsLeft, ChevronsRight, LayoutGrid } from "lucide-react";
import { NAV_ITEMS } from "./nav";
import { useAlerts } from "@/lib/hooks";

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const { data: alerts } = useAlerts("critical");
  const criticalCount = alerts?.length ?? 0;

  return (
    <aside
      className={`flex h-screen flex-col border-r border-slate-800 bg-slate-950 transition-all ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-4">
        <LayoutGrid size={20} className="shrink-0 text-sky-400" />
        {!collapsed && (
          <span className="text-sm font-semibold tracking-wide text-slate-100">MASTER CONTROL</span>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={`relative mx-2 my-0.5 flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "bg-sky-500/10 text-sky-300"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              }`}
              title={collapsed ? label : undefined}
            >
              <Icon size={17} className="shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
              {!collapsed && label === "Alerts" && criticalCount > 0 && (
                <span className="ml-auto rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
                  {criticalCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <button
        onClick={() => setCollapsed((v) => !v)}
        className="flex items-center gap-2 border-t border-slate-800 px-4 py-3 text-xs text-slate-500 hover:text-slate-300"
      >
        {collapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
        {!collapsed && "Collapse"}
      </button>
    </aside>
  );
}
