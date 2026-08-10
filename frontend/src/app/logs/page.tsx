import Link from "next/link";
import { UnavailableState } from "@/components/ui/States";

export default function LogsPage() {
  return (
    <UnavailableState reason="There's no structured, searchable log store (no logs table, no /api/logs endpoint). The closest real equivalent is each task's event timeline — open a task from the Tasks page, or an agent's recent events from its Agent Detail page.">
      <div className="flex gap-4">
        <Link href="/tasks" className="text-sm text-sky-400 hover:underline">
          Go to Tasks →
        </Link>
        <Link href="/agents" className="text-sm text-sky-400 hover:underline">
          Go to Agents →
        </Link>
      </div>
    </UnavailableState>
  );
}
