import { useQuery } from "@tanstack/react-query";
import { HeartPulse } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

const statusStyles: Record<string, string> = {
  ok: "bg-green-100 text-green-700",
  degraded: "bg-amber-100 text-amber-700",
  error: "bg-red-100 text-red-700",
};

export function AdminSystemHealth() {
  const token = useAuthStore((s) => s.token);
  const q = useQuery({
    queryKey: ["admin-health"],
    queryFn: () => adminApi.systemHealth(token!),
    enabled: !!token,
  });
  const d = q.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="System Health"
        subtitle="Backend, database, AI models, security and audit-chain diagnostics"
        icon={HeartPulse}
        actions={
          <Button variant="outline" onClick={() => q.refetch()}>
            Refresh
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Overall status:
            <span className={`rounded-full px-3 py-0.5 text-sm font-semibold ${statusStyles[d?.overall ?? ""] ?? "bg-[var(--muted)]"}`}>
              {(d?.overall ?? "loading").toUpperCase()}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {d
            ? Object.entries(d.checks).map(([name, c]) => (
                <div key={name} className="rounded-lg border border-[var(--border)] p-3">
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${statusStyles[c.status]?.includes("green") ? "bg-green-500" : statusStyles[c.status]?.includes("amber") ? "bg-amber-500" : "bg-red-500"}`} />
                    <span className="font-medium capitalize">{name.replace(/_/g, " ")}</span>
                    <span className={`ml-auto rounded-full px-2 py-0.5 text-xs font-semibold ${statusStyles[c.status] ?? "bg-[var(--muted)]"}`}>{c.status.toUpperCase()}</span>
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted-foreground)]">{c.detail}</p>
                </div>
              ))
            : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Record counts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {d
              ? Object.entries(d.counts).map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-[var(--muted)] px-4 py-2">
                    <p className="text-lg font-bold">{v}</p>
                    <p className="text-xs capitalize text-[var(--muted-foreground)]">{k.replace(/_/g, " ")}</p>
                  </div>
                ))
              : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
