import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ClipboardCheck, XCircle } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

type Status = "pending" | "approved" | "rejected";

export function AdminApprovals() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Status>("pending");
  const [comments, setComments] = useState<Record<string, string>>({});

  const list = useQuery({
    queryKey: ["admin-approvals", status],
    queryFn: () => adminApi.approvals(token!, status),
    enabled: !!token,
  });
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-approvals"] });
    queryClient.invalidateQueries({ queryKey: ["admin-cc"] });
  };

  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "approve" | "reject" }) =>
      adminApi.decideApproval(id, decision, comments[id] ?? "", token!),
    onSuccess: invalidate,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Global Approval Center"
        subtitle="Decide every agent write request at the institutional level"
        icon={ClipboardCheck}
        actions={
          <div className="flex gap-1 rounded-full bg-[var(--muted)] p-1">
            {(["pending", "approved", "rejected"] as Status[]).map((s) => (
              <Button key={s} size="sm" variant={status === s ? "default" : "ghost"} onClick={() => setStatus(s)}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </Button>
            ))}
          </div>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>{status.charAt(0).toUpperCase() + status.slice(1)} requests ({list.data?.length ?? 0})</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {(list.data ?? []).map((a) => (
            <div key={a.id} className="rounded-lg border border-[var(--border)] p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-[var(--primary)]/10 px-2 py-0.5 font-mono text-xs text-[var(--primary)]">{a.id.slice(0, 8)}</span>
                <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-semibold text-sky-700">{a.intent}</span>
                <span className="ml-auto text-xs text-[var(--muted-foreground)]">{new Date(a.created_at).toLocaleString()}</span>
              </div>
              <pre className="mt-2 overflow-x-auto rounded-lg bg-[var(--muted)] p-3 text-xs">
                {JSON.stringify(a.payload, null, 2)}
              </pre>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Input
                  placeholder="Comment (optional)"
                  value={comments[a.id] ?? ""}
                  onChange={(e) => setComments((c) => ({ ...c, [a.id]: e.target.value }))}
                  className="max-w-sm"
                />
                <Button size="sm" disabled={decide.isPending} onClick={() => decide.mutate({ id: a.id, decision: "approve" })}>
                  <CheckCircle2 className="h-4 w-4" /> Approve
                </Button>
                <Button size="sm" variant="destructive" disabled={decide.isPending} onClick={() => decide.mutate({ id: a.id, decision: "reject" })}>
                  <XCircle className="h-4 w-4" /> Reject
                </Button>
              </div>
            </div>
          ))}
          {(list.data ?? []).length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No {status} requests.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
