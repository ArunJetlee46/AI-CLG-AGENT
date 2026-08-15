import { api } from "@/core/lib/api";

export interface AuditRow {
  id: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  approval_id: string | null;
  payload: Record<string, unknown>;
  hash: string;
  created_at: string;
}

export const auditApi = {
  audit: (token: string, limit = 100) => api<AuditRow[]>(`/audit?limit=${limit}`, {}, token),
  approvals: (token: string, status = "pending") => api<{ id: string; intent: string; payload: Record<string, unknown>; status: string; created_at: string }[]>(`/approvals?status=${status}`, {}, token),
  decideApproval: (id: string, decision: "approve" | "reject", comment: string, token: string) =>
    api<{ ok: boolean }>(`/approvals/${id}`, { method: "POST", body: JSON.stringify({ decision, comment }) }, token),
};
