import { api } from "@/core/lib/api";

export interface ResourceRow {
  id: string;
  name: string;
  resource_type: string;
  capacity: number;
  location: string;
  status: string;
  utilization: number;
  notes: string;
  source: string;
}

export interface ResourcesReport {
  resources: ResourceRow[];
  count: number;
  status_counts: Record<string, number>;
}

export interface BackupRow {
  id: string;
  filename: string;
  kind: string;
  status: string;
  size_bytes: number;
  note: string;
  created_at: string;
}

export const resourcesApi = {
  resources: (token: string) => api<ResourcesReport>("/admin/resources", {}, token),
  createResource: (
    body: { name: string; resource_type?: string; capacity?: number; location?: string; status?: string; utilization?: number; notes?: string },
    token: string
  ) => api<ResourceRow>("/admin/resources", { method: "POST", body: JSON.stringify(body) }, token),
  updateResource: (id: string, body: { status?: string; utilization?: number }, token: string) =>
    api<ResourceRow>(`/admin/resources/${id}`, { method: "PATCH", body: JSON.stringify(body) }, token),

  backups: (token: string) => api<BackupRow[]>("/admin/backups", {}, token),
  createBackup: (token: string) => api<BackupRow & { snapshot?: Record<string, number> }>("/admin/backups", { method: "POST" }, token),
  restoreBackup: (id: string, token: string) =>
    api<{ ok: boolean; message: string }>(`/admin/backups/${id}/restore`, { method: "POST" }, token),
};
