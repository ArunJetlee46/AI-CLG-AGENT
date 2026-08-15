import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, UserCog, UserPlus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { toast } from "@/core/components/ui/toast";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi, type AdminUser } from "@/modules/admin/api";

const roleStyles: Record<string, string> = {
  admin: "bg-purple-100 text-purple-700",
  lecturer: "bg-sky-100 text-sky-700",
  placement: "bg-emerald-100 text-emerald-700",
  student: "bg-orange-100 text-orange-700",
};

export function AdminUsers() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("student");
  const [email, setEmail] = useState("");

  const users = useQuery({ queryKey: ["admin-users"], queryFn: () => adminApi.users(token!), enabled: !!token });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-users"] });

  const create = useMutation({
    mutationFn: (body: { username: string; password: string; role: string; email?: string }) => adminApi.createUser(body, token!),
    onSuccess: () => {
      invalidate();
      toast.success("User created", `${username} added successfully`);
      setUsername("");
      setPassword("");
      setRole("student");
      setEmail("");
    },
    onError: () => toast.error("Create failed", "Could not create the user account"),
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: { role?: string; is_active?: boolean; password?: string } }) => adminApi.updateUser(id, body, token!),
    onSuccess: () => {
      invalidate();
      toast.success("User updated");
    },
    onError: () => toast.error("Update failed"),
  });

  const changeRole = (u: AdminUser, role: string) => update.mutate({ id: u.id, body: { role } });
  const toggleActive = (u: AdminUser) => update.mutate({ id: u.id, body: { is_active: !u.is_active } });
  const resetPassword = (u: AdminUser) => {
    const pwd = prompt(`New password for ${u.username}:`, "NewPass@123");
    if (pwd) update.mutate({ id: u.id, body: { password: pwd } });
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="User Management & RBAC"
        subtitle="Accounts, roles, activation and access control"
        icon={UserCog}
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserPlus className="h-4 w-4" /> Create Account
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Username
            <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="john.doe" className="w-44" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Password
            <Input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="w-44" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Role
            <select value={role} onChange={(e) => setRole(e.target.value)} className="h-10 rounded-md border border-[var(--border)] bg-transparent px-3 text-sm">
              <option value="student">Student</option>
              <option value="lecturer">Lecturer</option>
              <option value="placement">Placement Officer</option>
              <option value="admin">Admin</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Email
            <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="optional" className="w-44" />
          </label>
          <Button
            disabled={!username || !password || create.isPending}
            loading={create.isPending}
            onClick={() => create.mutate({ username, password, role, email: email || undefined })}
          >
            Create User
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Accounts ({users.data?.length ?? 0})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="table-shell">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {(users.data ?? []).map((u) => (
                  <tr key={u.id}>
                    <td className="font-medium">{u.username}</td>
                    <td>
                      <select
                        value={u.role}
                        onChange={(e) => changeRole(u, e.target.value)}
                        className={`rounded-full px-2 py-0.5 text-xs font-semibold ${roleStyles[u.role] ?? "bg-[var(--muted)]"}`}
                      >
                        <option value="admin">admin</option>
                        <option value="lecturer">lecturer</option>
                        <option value="placement">placement</option>
                        <option value="student">student</option>
                      </select>
                    </td>
                    <td className="text-[var(--muted-foreground)]">{u.email ?? "—"}</td>
                    <td>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${u.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                        {u.is_active ? "ACTIVE" : "DISABLED"}
                      </span>
                    </td>
                    <td className="text-right">
                      <Button size="sm" variant="outline" onClick={() => resetPassword(u)}>
                        <KeyRound className="h-3 w-3" /> Reset
                      </Button>{" "}
                      <Button size="sm" variant={u.is_active ? "destructive" : "outline"} onClick={() => toggleActive(u)}>
                        {u.is_active ? "Disable" : "Enable"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
