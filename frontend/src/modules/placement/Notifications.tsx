import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Megaphone } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { placementApi } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

export function Notifications() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();

  const notifs = useQuery({ queryKey: ["pl-notifs"], queryFn: () => placementApi.notifications(token!), enabled: !!token });

  const markRead = useMutation({
    mutationFn: (id: string) => placementApi.markNotificationRead(id, token!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pl-notifs"] }),
  });

  const n = notifs.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Placement Notifications" subtitle="Students shortlisted and notified for drives — officer-generated, delivered in-app" icon={Megaphone} accent="bg-pink-100 text-pink-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Megaphone className="h-4 w-4" /> {n?.total ?? 0} sent · <Badge tone="warning">{n?.unread ?? 0} unread</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-1.5">
          {(n?.entries ?? []).length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No notifications yet — shortlist candidates on the Matching page and notify them.</p>}
          {(n?.entries ?? []).map((e) => (
            <div key={e.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--border)] px-3 py-2">
              <span className="font-mono text-sm font-medium">{e.student_id}</span>
              <Badge tone={e.status === "read" ? "success" : "warning"}>{e.status}</Badge>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{e.title}</p>
                <p className="truncate text-xs text-[var(--muted-foreground)]">{e.body}</p>
              </div>
              <span className="text-[11px] text-[var(--muted-foreground)]">{new Date(e.created_at).toLocaleString()}</span>
              {e.status === "sent" && (
                <Button size="sm" variant="outline" onClick={() => markRead.mutate(e.id)}>Mark read</Button>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
