import Link from "next/link";
import { UnavailableState } from "@/components/ui/States";

export default function WorkflowsPage() {
  return (
    <UnavailableState reason="There's no separate 'workflow definition' concept in this system distinct from a task — every video follows the same fixed pipeline (see a channel's Production Pipeline view). For a list of actual pipeline runs, see the Tasks page instead.">
      <Link href="/tasks" className="text-sm text-sky-400 hover:underline">
        Go to Tasks →
      </Link>
    </UnavailableState>
  );
}
