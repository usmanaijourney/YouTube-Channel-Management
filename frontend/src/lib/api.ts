import type {
  Alert,
  AgentDetail,
  ChannelDetail,
  ChannelSummary,
  IntegrationStatus,
  OrchestratorView,
  Schedule,
  SystemHealth,
  TaskDetail,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function proxyFetch<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(`/api/proxy/${path}`, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, value);
    }
  }

  let res: Response;
  try {
    res = await fetch(url.toString());
  } catch {
    throw new ApiError(0, "Network error — could not reach the dashboard server");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore body parse failure, keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export const api = {
  systemHealth: () => proxyFetch<SystemHealth>("system/health"),
  channels: () => proxyFetch<ChannelSummary[]>("channels"),
  channelDetail: (channelId: string) => proxyFetch<ChannelDetail>(`channels/${channelId}`),
  agentDetail: (channelId: string, agentType: string) =>
    proxyFetch<AgentDetail>(`channels/${channelId}/agents/${agentType}`),
  taskDetail: (channelId: string, taskId: string) =>
    proxyFetch<TaskDetail>(`channels/${channelId}/tasks/${taskId}`),
  alerts: (severity?: string) => proxyFetch<Alert[]>("alerts", { severity }),
  integrations: () => proxyFetch<IntegrationStatus[]>("integrations"),
  schedules: () => proxyFetch<Schedule[]>("schedules"),
  orchestrator: () => proxyFetch<OrchestratorView>("orchestrator"),
};
