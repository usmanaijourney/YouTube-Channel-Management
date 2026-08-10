/** Maps the workflow's actual task states (channel_manager/workflow.py) onto
 * the 7-stage pipeline visualization the platform spec describes. */
export const PIPELINE_STAGES = [
  { label: "Topic Research", states: ["CREATED", "TOPIC_RESEARCH"] },
  { label: "Topic Approval", states: ["TOPIC_EVALUATION", "TOPIC_APPROVED"] },
  { label: "Script", states: ["SCRIPT_DRAFTING", "SCRIPT_APPROVED"] },
  {
    label: "Voice Over + Video/Visuals",
    states: ["PRODUCTION_FANOUT", "VOICE_OVER_DONE", "VISUAL_PLANNING_IN_PROGRESS", "VIDEO_DONE", "PRODUCTION_JOIN"],
  },
  { label: "Quality Control", states: ["QUALITY_CHECK"] },
  { label: "YouTube Upload", states: ["UPLOAD_IN_PROGRESS", "UPLOAD_DONE"] },
  { label: "WhatsApp Notification", states: ["NOTIFY", "REPORTED", "CLOSED"] },
] as const;

export type StageStatus = "completed" | "processing" | "waiting" | "failed";

export function stageStatuses(currentState: string, failedFromState?: string | null): StageStatus[] {
  if (currentState === "FAILED" && failedFromState) {
    const failedStageIndex = PIPELINE_STAGES.findIndex((s) => (s.states as readonly string[]).includes(failedFromState));
    return PIPELINE_STAGES.map((_, i) => {
      if (failedStageIndex === -1) return "waiting";
      if (i < failedStageIndex) return "completed";
      if (i === failedStageIndex) return "failed";
      return "waiting";
    });
  }

  const currentStageIndex = PIPELINE_STAGES.findIndex((s) => (s.states as readonly string[]).includes(currentState));
  return PIPELINE_STAGES.map((_, i) => {
    if (currentStageIndex === -1) return "waiting";
    if (i < currentStageIndex) return "completed";
    if (i === currentStageIndex) return currentState === "CLOSED" ? "completed" : "processing";
    return "waiting";
  });
}
