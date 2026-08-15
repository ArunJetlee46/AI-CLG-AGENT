import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Megaphone, Pin, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

const AUDIENCE_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "Everyone" },
  { value: "student", label: "Students" },
  { value: "lecturer", label: "Faculty" },
  { value: "placement", label: "Placement" },
  { value: "admin", label: "Admin" },
];

const ROLE_LABELS: Record<string, string> = {
  student: "Student",
  lecturer: "Faculty",
  placement: "Placement",
  admin: "Admin",
};

const AUDIENCE_LABELS: Record<string, string> = Object.fromEntries(
  AUDIENCE_OPTIONS.map((o) => [o.value, o.label])
);

export function Announcements() {
  const token = useAuthStore((s) => s.token);
  const role = useAuthStore((s) => s.role);
  const username = useAuthStore((s) => s.username);
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState("all");
  const [pinned, setPinned] = useState(false);

  const list = useQuery({ queryKey: ["admin-announcements"], queryFn: () => adminApi.announcements(token!), enabled: !!token });
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-announcements"] });
    queryClient.invalidateQueries({ queryKey: ["notifs"] });
  };

  const create = useMutation({
    mutationFn: (b: { title: string; body: string; audience?: string; pinned?: boolean }) => adminApi.createAnnouncement(b, token!),
    onSuccess: () => { invalidate(); setTitle(""); setBody(""); setAudience("all"); setPinned(false); },
  });
  const remove = useMutation({ mutationFn: (id: string) => adminApi.deleteAnnouncement(id, token!), onSuccess: invalidate });

  const canDelete = (createdBy: string) => role === "admin" || createdBy === username;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Announcements" subtitle="Institutional broadcast board" icon={Megaphone} />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Plus className="h-4 w-4" /> Post Announcement</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Title
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Convocation 2026" className="w-52" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Body
            <Input value={body} onChange={(e) => setBody(e.target.value)} placeholder="Details…" className="w-80" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Audience
            <select value={audience} onChange={(e) => setAudience(e.target.value)} className="h-10 rounded-md border border-[var(--border)] bg-transparent px-3 text-sm">
              {AUDIENCE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
            <input type="checkbox" checked={pinned} onChange={(e) => setPinned(e.target.checked)} /> Pin
          </label>
          <Button disabled={!title || !body || create.isPending} onClick={() => create.mutate({ title, body, audience, pinned })}>
            Post
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Board ({list.data?.length ?? 0})</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {(list.data ?? []).map((a) => (
            <div key={a.id} className="flex items-start gap-3 border-b border-[var(--border)] pb-3">
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-2 font-medium">
                  {a.pinned && <Pin className="h-3.5 w-3.5 text-amber-500" />}
                  {a.title}
                </p>
                <p className="text-sm text-[var(--muted-foreground)]">{a.body}</p>
                <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                  {a.created_by}{a.created_role ? ` (${ROLE_LABELS[a.created_role] ?? a.created_role})` : ""} · to {AUDIENCE_LABELS[a.audience] ?? a.audience} · {new Date(a.created_at).toLocaleString()}
                </p>
              </div>
              {canDelete(a.created_by) && (
                <Button size="sm" variant="ghost" onClick={() => remove.mutate(a.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
          {(list.data ?? []).length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No announcements.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
