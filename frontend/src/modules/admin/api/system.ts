import { api } from "@/core/lib/api";

export interface SystemHealth {
  overall: string;
  checks: Record<string, { status: string; detail: string }>;
  counts: Record<string, number>;
}

export const systemApi = {
  systemHealth: (token: string) => api<SystemHealth>("/admin/system-health", {}, token),
};
