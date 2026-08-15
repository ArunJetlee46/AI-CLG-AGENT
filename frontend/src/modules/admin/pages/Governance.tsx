import { useQuery } from "@tanstack/react-query";
import { Landmark, Lightbulb, Power, ShieldAlert } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

export function AdminGovernance() {
  const token = useAuthStore((s) => s.token);
  const q = useQuery({ queryKey: ["admin-governance"], queryFn: () => adminApi.governance(token!), enabled: !!token });
  const d = q.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Governance Center" subtitle="Safety rails, approvals, audit integrity and model governance" icon={Landmark} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><ShieldAlert className="h-4 w-4" /> Safety</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1 text-sm">
            <p className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${d?.safety.execution_allowed ? "bg-green-500" : "bg-red-500"}`} />
              AI Execution {d?.safety.execution_allowed ? "ENABLED" : "PAUSED"}
            </p>
            <p className="text-xs text-[var(--muted-foreground)]">read-only mode: {d?.safety.read_only ? "ON" : "OFF"}</p>
            <p className="text-xs text-[var(--muted-foreground)]">execution_enabled: {String(d?.safety.execution_enabled)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Power className="h-4 w-4" /> Approvals</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1 text-sm">
            <p className="text-2xl font-bold">{d?.approvals.pending ?? 0} pending</p>
            <p className="text-xs text-[var(--muted-foreground)]">{d?.approvals.total ?? 0} total requests</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Audit Integrity</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1 text-sm">
            <p className="text-2xl font-bold">{d?.audit.events ?? 0} events</p>
            <p className="text-xs text-[var(--muted-foreground)]">{d?.audit.decision_cards ?? 0} decision cards</p>
            <p className="text-xs text-[var(--muted-foreground)]">hash-chain verified end-to-end</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Model Governance</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1 text-sm">
            <p className="text-2xl font-bold">{d?.models.active ?? 0} active</p>
            <p className="text-xs text-[var(--muted-foreground)]">{d?.models.total ?? 0} models registered</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-4 w-4" /> Governance recommendations
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {(d?.recommendations ?? []).map((r, i) => (
            <div key={i} className="flex items-start gap-2 border-b border-[var(--border)] pb-2 text-sm">
              <span className="mt-0.5 rounded-full bg-[var(--primary)]/10 px-2 py-0.5 text-xs font-semibold text-[var(--primary)]">{i + 1}</span>
              <p>{r}</p>
            </div>
          ))}
          {(d?.recommendations ?? []).length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">
              No recommendations. <Button size="sm" variant="outline" className="ml-2">Run health assessment</Button>
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
