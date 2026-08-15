import { clearSession, ensureFreshToken, refreshAccessToken } from "@/core/lib/auth-session";
import { useAuthStore } from "@/core/stores/auth";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit, retried: boolean, explicitToken?: string | null): Promise<T> {
  const accessToken = explicitToken ?? useAuthStore.getState().token;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (response.status === 401 && !retried && !path.startsWith("/auth/")) {
    const { refreshToken } = useAuthStore.getState();
    if (!refreshToken) {
      clearSession("Your session is no longer valid. Please sign in again.");
      throw new ApiError(401, "Session expired");
    }
    try {
      await refreshAccessToken();
    } catch (err) {
      throw err instanceof ApiError ? err : new ApiError(401, err instanceof Error ? err.message : "Session expired");
    }
    return request<T>(path, options, true);
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export async function api<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  await ensureFreshToken();
  return request<T>(path, options, false, token);
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserInfo {
  id: string;
  username: string;
  role: string;
  email: string;
}

export interface ChatResponse {
  intent: string;
  agent: string;
  answer: string;
  citations: string[];
  requires_approval: boolean;
  approval_id: string | null;
  decision_card_id: string | null;
  provider: string;
  model: string;
}

export interface PredictionRow {
  student_id: string;
  course_code: string;
  probability: number;
  risk_level: string;
  explanation: string;
  model_version: string;
}

export interface TaskPredictionRow {
  task: "performance" | "placement" | "attendance" | "dropout";
  student_id: string;
  course_code: string | null;
  pass_probability?: number;
  placement_probability?: number;
  absence_risk?: number;
  dropout_probability?: number;
  risk_level: string;
  action: string;
  explanation: string;
  explainer: string;
  contributions: Record<string, number>;
  model_version: string;
}

export interface ModelRecord {
  name: string;
  version: string;
  path: string;
  metrics: Record<string, unknown>;
  trained_at: string;
}

export interface ApprovalRow {
  id: string;
  intent: string;
  payload: Record<string, unknown>;
  status: string;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  app: string;
  env: string;
  db: string;
  llm_providers: string[];
}

export interface NotificationItem {
  id: string;
  type: string;
  severity: string;
  title: string;
  body: string;
  link: string;
  read: boolean;
  created_at: string;
}

export interface NotificationsPayload {
  entries: NotificationItem[];
  unread_count: number;
}

export const notificationsApi = {
  list: (token: string) => api<NotificationsPayload>("/notifications", {}, token),
  markRead: (id: string, token: string) =>
    api<{ id: string; read: boolean }>(`/notifications/${id}/read`, { method: "POST" }, token),
  markAllRead: (token: string) => api<{ updated: number }>("/notifications/read-all", { method: "POST" }, token),
};

export const authApi = {
  login: (username: string, password: string) =>
    api<LoginResponse>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: (token: string) => api<UserInfo>("/auth/me", {}, token),
};

export const agentApi = {
  chat: (message: string, token: string) =>
    api<ChatResponse>("/agents/chat", { method: "POST", body: JSON.stringify({ message }) }, token),
};

export const predictionApi = {
  live: (token: string) => api<PredictionRow[]>("/predictions/live", {}, token),
  all: (token: string, limit = 25) => api<TaskPredictionRow[]>(`/predictions/all?limit=${limit}`, {}, token),
  models: (token: string) => api<ModelRecord[]>("/predictions/models", {}, token),
};

export const approvalApi = {
  list: (token: string, status = "pending") => api<ApprovalRow[]>(`/approvals?status=${status}`, {}, token),
};

export const healthApi = {
  get: () => api<HealthResponse>("/health"),
};
