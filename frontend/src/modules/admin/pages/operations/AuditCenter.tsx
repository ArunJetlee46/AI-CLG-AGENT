import { useQuery } from "@tanstack/react-query";
import { ScrollText } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

export function AdminAuditCenter() {
  const token = useAuthStore((s) => s.token);
  const [limit, setLimit] = useState(100);

  const q = useQuery({
    queryKey: ["admin-audit", limit],
    queryFn: () => adminApi.audit(token!, limit),
    enabled: !!token,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Audit Center"
        subtitle="Tamper-evident hash-chained event log"
        icon={ScrollText}
        actions={
          <div className="flex gap-1 rounded-full bg-[var(--muted)] p-1">
            {[50, 100, 250].map((n) => (
              <Button key={n} size="sm" variant={limit === n ? "default" : "ghost"} onClick={() => setLimit(n)}>
                {n}
              </Button>
            ))}
          </div>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Events ({q.data?.length ?? 0})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                  <th className="pb-2">Time</th>
                  <th className="pb-2">Actor</th>
                  <th className="pb-2">Action</th>
                  <th className="pb-2">Entity</th>
                  <th className="pb-2">Approval</th>
                  <th className="pb-2">Hash (first 12)</th>
                </tr>
              </thead>
              <tbody>
                {(q.data ?? []).map((e) => (
                  <tr key={e.id} className="border-b border-[var(--border)]">
                    <td className="py-2 whitespace-nowrap text-xs text-[var(--muted-foreground)]">{new Date(e.created_at).toLocaleString()}</td>
                    <td className="py-2 font-mono text-xs font-medium">{e.actor}</td>
                    <td className="py-2">{e.action}</td>
                    <td className="py-2 font-mono text-xs text-[var(--muted-foreground)]">{e.entity_type}{e.entity_id ? `/${e.entity_id.slice(0, 8)}` : ""}</td>
                    <td className="py-2 font-mono text-xs text-[var(--muted-foreground)]">{e.approval_id ? e.approval_id.slice(0, 8) : "—"}</td>
                    <td className="py-2 font-mono text-xs text-[var(--muted-foreground)]">{e.hash.slice(0, 12)}</td>
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
