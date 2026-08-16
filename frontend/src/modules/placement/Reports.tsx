import { useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { EmptyState } from "@/core/components/ui/empty-state";
import { Skeleton } from "@/core/components/ui/skeleton";
import { placementApi } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

export function Reports() {
  const token = useAuthStore((s) => s.token);
  const report = useQuery({
    queryKey: ["pl-report-full"],
    queryFn: () => placementApi.fullReport(token!),
    enabled: !!token,
    staleTime: 5 * 60_000,
  });
  const r = report.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Automated Placement Reports" subtitle="One-click cohort placement report — funnel, prediction, departments, salary, skill demand" icon={FileText} accent="bg-violet-100 text-violet-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm">Cohort placement report <span className="ml-2 font-normal text-[var(--muted-foreground)]">{r?.generated_at ? new Date(r.generated_at).toLocaleString() : ""}</span></CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 text-sm">
          {report.isLoading && !r && (
            <div className="flex flex-col gap-4">
              <Skeleton className="h-16 w-full rounded-lg" />
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-16 rounded-lg" />
                ))}
              </div>
              <Skeleton className="h-24 w-full rounded-lg" />
            </div>
          )}
          {report.isError && !r && (
            <EmptyState
              title="Could not generate the report"
              description="Placement report generation failed. Try again."
              icon={FileText}
            />
          )}
          {r && (
            <>
              <p className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/30 p-3">{r.summary}</p>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
                {[
                  { label: "Cohort", value: r.funnel.cohort },
                  { label: "Eligible", value: r.funnel.eligible },
                  { label: "Shortlisted", value: r.funnel.shortlisted },
                  { label: "Offers", value: r.funnel.offers },
                  { label: "Joined", value: r.funnel.joined },
                  { label: "Predicted rate", value: r.prediction.predicted_placement_rate != null ? `${Math.round(r.prediction.predicted_placement_rate * 100)}%` : "—" },
                  { label: "At risk", value: r.high_risk_students },
                  { label: "Avg CTC", value: r.salary.avg_ctc != null ? `${r.salary.avg_ctc} LPA` : "—" },
                  { label: "Max CTC", value: r.salary.max_ctc != null ? `${r.salary.max_ctc} LPA` : "—" },
                  { label: "Offers made", value: r.salary.offered },
                  { label: "Joined", value: r.salary.joined },
                ].map((x) => (
                  <div key={x.label} className="rounded-lg border border-[var(--border)] p-3 text-center">
                    <p className="text-lg font-bold">{x.value}</p>
                    <p className="text-[11px] text-[var(--muted-foreground)]">{x.label}</p>
                  </div>
                ))}
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold text-[var(--muted-foreground)]">Top in-demand skills</p>
                <div className="flex flex-wrap gap-1">
                  {r.top_skills.map((s) => (
                    <span key={s.skill} className="rounded-full bg-[var(--muted)] px-2 py-0.5 text-xs">{s.skill} ({s.demand})</span>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold text-[var(--muted-foreground)]">Departments</p>
                <div className="flex flex-col gap-1.5">
                  {r.departments.map((d) => (
                    <div key={d.program} className="flex items-center gap-2 border-b border-[var(--border)] pb-1">
                      <span className="w-44 truncate">{d.program}</span>
                      <span className="text-xs text-[var(--muted-foreground)]">{d.students} students</span>
                      <span className="ml-auto text-xs">{d.ready} ready · {d.offers} offers{d.avg_ctc ? ` · avg ${d.avg_ctc} LPA` : ""}</span>
                    </div>
                  ))}
                </div>
              </div>
              <p className="text-xs text-[var(--muted-foreground)]">method: {r.method} · cached for 5 minutes</p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
