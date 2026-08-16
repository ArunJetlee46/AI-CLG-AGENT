import { api } from "@/core/lib/api";

export interface AdminUser {
  id: string;
  username: string;
  role: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface Announcement {
  id: string;
  title: string;
  body: string;
  audience: string;
  pinned: boolean;
  created_by: string;
  created_role: string;
  created_at: string;
}

export const usersApi = {
  users: (token: string) => api<AdminUser[]>("/admin/users", {}, token),
  createUser: (body: { username: string; password: string; role: string; email?: string }, token: string) =>
    api<AdminUser>("/admin/users", { method: "POST", body: JSON.stringify(body) }, token),
  updateUser: (id: string, body: { role?: string; is_active?: boolean; password?: string }, token: string) =>
    api<AdminUser>(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }, token),

  announcements: (token: string) => api<Announcement[]>("/admin/announcements", {}, token),
  createAnnouncement: (body: { title: string; body: string; audience?: string; pinned?: boolean }, token: string) =>
    api<Announcement>("/admin/announcements", { method: "POST", body: JSON.stringify(body) }, token),
  deleteAnnouncement: (id: string, token: string) =>
    api<{ ok: boolean }>(`/admin/announcements/${id}`, { method: "DELETE" }, token),
};
