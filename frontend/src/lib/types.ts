export type HealthStatus = "healthy" | "error" | "mocked";
export type TaskState = string; // backend uses free-form state strings (CREATED, TOPIC_RESEARCH, ..., CLOSED, FAILED)

export interface SystemHealth {
  total_channels: number;
  active_channels: number;
  channels_with_problems: number;
  paused_channels: number;
  total_tasks: number;
  tasks_completed: number;
  tasks_failed: number;
  tasks_in_progress: number;
  cost_total: number;
  open_critical_alerts: number;
}

export interface ChannelSummary {
  channel_id: string;
  name: string;
  niche: string;
  status: string;
  created_at: string;
  schedule: { videos_per_day?: number; preferred_hours_utc?: number[] };
  current_task_count: number;
  tasks_completed: number;
  tasks_failed: number;
  videos_produced: number;
  videos_uploaded: number;
  cost_total: number;
}

export interface AgentRow {
  agent_id: string;
  channel_id: string;
  agent_type: string;
  status: string;
  last_heartbeat: string | null;
  last_success: string | null;
  last_failure: string | null;
  failure_count: number;
  avg_exec_ms: number | null;
  retry_count: number;
}

export interface TaskSummary {
  task_id: string;
  state: TaskState;
  topic: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChannelDetail extends ChannelSummary {
  youtube_channel_ref: string | null;
  agents: AgentRow[];
  recent_tasks: TaskSummary[];
}

export interface TaskEvent {
  id: number;
  task_id: string;
  from_state: string | null;
  to_state: string;
  agent_id: string | null;
  payload: Record<string, unknown> | null;
  error: { stage?: string; reason?: string; [key: string]: unknown } | null;
  created_at: string;
}

export interface TaskDetail {
  task_id: string;
  channel_id: string;
  state: TaskState;
  topic: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  events: TaskEvent[];
}

export interface AgentDetail {
  channel_id: string;
  agent_type: string;
  instances: AgentRow[];
  recent_events: TaskEvent[];
}

export interface Alert {
  id: number;
  channel_id: string | null;
  event_type: string;
  severity: "critical" | "warning" | "info" | string;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface IntegrationStatus {
  service_name: string;
  status: HealthStatus;
  last_check_at: string | null;
  last_success_at: string | null;
  response_time_ms: number | null;
  error_count: number;
  last_error: string | null;
}

export interface Schedule {
  channel_id: string;
  enabled: boolean;
  preferred_hours_utc: number[];
  last_run_at: string | null;
  last_run_status: string | null;
  next_run_estimate: string | null;
}

export interface OrchestratorCycleStatus {
  status: string;
  started_at: string | null;
  last_cycle_at: string | null;
  managed_channels: number;
  active_slots: number;
  max_slots: number;
  cycles_run: number;
}

export interface OrchestratorView {
  status: OrchestratorCycleStatus | null;
  recent_events: Alert[];
}
