import { api } from "@/core/lib/api";

export interface ModelEntry {
  id: string;
  name: string;
  version: string;
  path: string;
  metrics: Record<string, unknown>;
  is_active: boolean;
  trained_at: string;
}

export interface ModelReport {
  models: ModelEntry[];
  count: number;
  active: ModelEntry | null;
}

export const modelsApi = {
  models: (token: string) => api<ModelReport>("/admin/models", {}, token),
  registerModel: (body: { name: string; version: string; path?: string; metrics?: Record<string, unknown> }, token: string) =>
    api<ModelEntry>("/admin/models", { method: "POST", body: JSON.stringify(body) }, token),
  activateModel: (id: string, token: string) =>
    api<ModelEntry>(`/admin/models/${id}/activate`, { method: "POST" }, token),
};
