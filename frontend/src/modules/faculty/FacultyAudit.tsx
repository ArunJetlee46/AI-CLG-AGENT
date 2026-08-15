import { useQuery } from "@tanstack/react-query";
import { ScrollText } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { facultyApi } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";

const PAGE = 30;

const actionTone = (action: string) =>
  action.endsWith("created") || action.endsWith("_proposed") ? "warning" : action.includes("approve") ? "success" : "destructive";

export function FacultyAudit() {
  const token = useAuthStore((s) => s.token);
  const [offset, setOffset] = useState(0);

  const audit = useQuery({
    queryKey: ["fac-audit", offset],
    queryFn: () => facultyApi.auditLog(token!, PAGE, offset),
    enabled: !!token,
  });

  const entries = audit.data?.entries ?? [];
  const total = audit.data?.total ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Faculty Audit Log" subtitle="Every proposed, approved and executed faculty action (hash-chained)" icon={ScrollText} accent="bg-slate-200 text-slate-700" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <ScrollText className="h-4 w-4" /> {total} event(s)
            <span className="ml-auto text-xs font-normal text-[var(--muted-foreground)]">{audit.data?.staff_id}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-1.5">
          {entries.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No audited actions yet.</p>}
          {entries.map((e) => {
            const payload = e.payload as Record<string, unknown>;
            return (
              <div key={e.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--border)] px-3 py-2">
                <Badge tone={actionTone(e.action)} className="shrink-0 font-mono">{e.action}</Badge>
                <span className="min-w-0 flex-1 text-sm">
                  {typeof payload.student_id === "string" ? <span className="font-mono">{payload.student_id}</span> : null}
                  {typeof payload.course_code === "string" && payload.course_code ? <span className="text-[var(--muted-foreground)]"> · {payload.course_code}</span> : null}
                  {typeof payload.plan === "string" ? <span className="text-xs text-[var(--muted-foreground)]"> · {payload.plan}</span> : null}
                </span>
                <span className="text-[11px] text-[var(--muted-foreground)]">{new Date(e.created_at).toLocaleString()}</span>
              </div>
            );
          })}
          {total > PAGE && (
            <div className="mt-2 flex items-center gap-2">
              <Button size="sm" variant="outline" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - PAGE))}>
                Previous
              </Button>
              <span className="text-xs text-[var(--muted-foreground)]">
                {offset + 1}–{Math.min(offset + PAGE, total)} of {total}
              </span>
              <Button size="sm" variant="outline" disabled={offset + PAGE >= total} onClick={() => setOffset((o) => o + PAGE)}>
                Next
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
