import { useQuery } from "@tanstack/react-query";
import { Award } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

export function AdminAccreditation() {
  const token = useAuthStore((s) => s.token);
  const q = useQuery({ queryKey: ["admin-accreditation"], queryFn: () => adminApi.accreditation(token!), enabled: !!token });
  const d = q.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Accreditation Readiness" subtitle="NAAC-style criteria scorecard" icon={Award} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard label="Overall score" value={d?.overall_score} sub="out of 100" icon={Award} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Projected grade" value={d?.grade} icon={Award} accent="bg-violet-100 text-violet-600" />
        <StatCard label="Criteria met" value={`${d?.met_count ?? 0} / ${d?.total_checks ?? 0}`} icon={Award} accent="bg-emerald-100 text-emerald-600" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Criteria scores</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {d
              ? Object.entries(d.criteria).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-2 text-sm">
                    <span className="w-44 capitalize">{k.replace(/_/g, " ")}</span>
                    <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                      <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${v}%` }} />
                    </span>
                    <span className="w-10 text-right">{v}</span>
                  </div>
                ))
              : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Readiness checklist</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {(d?.readiness ?? []).map((r) => (
              <div key={r.metric} className="flex items-center gap-2 border-b border-[var(--border)] pb-2 text-sm">
                <span className={`h-2 w-2 shrink-0 rounded-full ${r.met ? "bg-green-500" : "bg-red-500"}`} />
                <span className="capitalize">{r.metric.replace(/_/g, " ")}</span>
                <span className={`ml-auto rounded-full px-2 py-0.5 text-xs font-semibold ${r.met ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                  {r.met ? "MET" : "GAP"}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
