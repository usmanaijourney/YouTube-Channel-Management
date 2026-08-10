import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";
import { PIPELINE_STAGES, StageStatus, stageStatuses } from "@/lib/pipeline";

const ICON: Record<StageStatus, React.ReactNode> = {
  completed: <CheckCircle2 size={16} className="text-emerald-400" />,
  processing: <Loader2 size={16} className="animate-spin text-sky-400" />,
  waiting: <CircleDashed size={16} className="text-slate-600" />,
  failed: <XCircle size={16} className="text-red-400" />,
};

const TEXT_COLOR: Record<StageStatus, string> = {
  completed: "text-emerald-400",
  processing: "text-sky-400",
  waiting: "text-slate-600",
  failed: "text-red-400",
};

export function PipelineVisualization({
  currentState,
  failedFromState,
}: {
  currentState: string;
  failedFromState?: string | null;
}) {
  const statuses = stageStatuses(currentState, failedFromState);

  return (
    <div className="flex flex-col gap-0">
      {PIPELINE_STAGES.map((stage, i) => (
        <div key={stage.label} className="flex gap-3">
          <div className="flex flex-col items-center">
            {ICON[statuses[i]]}
            {i < PIPELINE_STAGES.length - 1 && (
              <div className={`my-1 h-6 w-px ${statuses[i] === "completed" ? "bg-emerald-500/40" : "bg-slate-800"}`} />
            )}
          </div>
          <div className={`pb-4 text-sm ${TEXT_COLOR[statuses[i]]}`}>{stage.label}</div>
        </div>
      ))}
    </div>
  );
}
