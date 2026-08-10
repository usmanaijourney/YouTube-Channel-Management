"use client";

import useSWR from "swr";
import { api } from "./api";

// 15s refresh matches the backend's own materialized-view-refresh cadence
// mentioned in the architecture doc (§14) — "live" without hammering the API.
const REFRESH_MS = 15_000;

export function useSystemHealth() {
  return useSWR("system-health", api.systemHealth, { refreshInterval: REFRESH_MS });
}

export function useChannels() {
  return useSWR("channels", api.channels, { refreshInterval: REFRESH_MS });
}

export function useChannelDetail(channelId: string | undefined) {
  return useSWR(channelId ? ["channel-detail", channelId] : null, () => api.channelDetail(channelId!), {
    refreshInterval: REFRESH_MS,
  });
}

export function useAgentDetail(channelId: string | undefined, agentType: string | undefined) {
  return useSWR(
    channelId && agentType ? ["agent-detail", channelId, agentType] : null,
    () => api.agentDetail(channelId!, agentType!),
    { refreshInterval: REFRESH_MS }
  );
}

export function useTaskDetail(channelId: string | undefined, taskId: string | undefined) {
  return useSWR(
    channelId && taskId ? ["task-detail", channelId, taskId] : null,
    () => api.taskDetail(channelId!, taskId!),
    { refreshInterval: REFRESH_MS }
  );
}

export function useAlerts(severity?: string) {
  return useSWR(["alerts", severity ?? "all"], () => api.alerts(severity), { refreshInterval: REFRESH_MS });
}

export function useIntegrations() {
  return useSWR("integrations", api.integrations, { refreshInterval: REFRESH_MS });
}

export function useSchedules() {
  return useSWR("schedules", api.schedules, { refreshInterval: REFRESH_MS });
}

export function useOrchestrator() {
  return useSWR("orchestrator", api.orchestrator, { refreshInterval: REFRESH_MS });
}

/** Aggregated client-side across every channel — no global /api/agents endpoint exists yet. */
export function useAllAgents() {
  return useSWR(
    "all-agents",
    async () => {
      const channels = await api.channels();
      const details = await Promise.all(channels.map((c) => api.channelDetail(c.channel_id)));
      return details.flatMap((d) => d.agents.map((a) => ({ ...a, channel_name: d.name })));
    },
    { refreshInterval: REFRESH_MS }
  );
}

/** Aggregated client-side across every channel, capped at each channel's recent_tasks (20).
 * No global/paginated task-list endpoint exists yet — see frontend/README.md limitations. */
export function useAllTasks() {
  return useSWR(
    "all-tasks",
    async () => {
      const channels = await api.channels();
      const details = await Promise.all(channels.map((c) => api.channelDetail(c.channel_id)));
      return details.flatMap((d) =>
        d.recent_tasks.map((t) => ({ ...t, channel_id: d.channel_id, channel_name: d.name }))
      );
    },
    { refreshInterval: REFRESH_MS }
  );
}
