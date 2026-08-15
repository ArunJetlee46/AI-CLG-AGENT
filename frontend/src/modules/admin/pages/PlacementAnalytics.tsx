import { useQuery } from "@tanstack/react-query";
import { Briefcase } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

function FunnelCard({ title, rows }: { title: string; rows: unknown[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">No data.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {(rows as { stage?: string; label?: string; name?: string; count?: number; students?: number; value?: number; salary?: number | null; avg_salary?: number | null }[]).map((row, i) => (
              <div key={i} className="flex items-center gap-2 border-b border-[var(--border)] pb-2 text-sm">
                <span className="w-44 truncate capitalize">{row.stage ?? row.label ?? row.name}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                  <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${row.count ?? row.students ?? 0}%` }} />
                </span>
                <span className="w-16 text-right">{row.count ?? row.students ?? row.value ?? row.salary ?? row.avg_salary ?? 0}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AdminPlacementAnalytics() {
  const token = useAuthStore((s) => s.token);
  const q = useQuery({ queryKey: ["admin-placement"], queryFn: () => adminApi.placementAnalytics(token!), enabled: !!token });
  const d = q.data;
  const funnel = (d?.funnel as { rows?: unknown[] })?.rows ?? [];
  const skill = (d?.skill_demand as { rows?: unknown[] })?.rows ?? [];
  const salary = (d?.salary as { rows?: unknown[] })?.rows ?? [];
  const departments = (d?.departments as { rows?: unknown[] })?.rows ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Placement Analytics" subtitle="University-wide placement pipeline (synced from placement module)" icon={Briefcase} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard label="Companies" value={d?.companies} icon={Briefcase} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Drives" value={d?.drives} icon={Briefcase} accent="bg-violet-100 text-violet-600" />
        <StatCard label="Forecast" value={(d?.prediction as { expected_placement_rate?: number })?.expected_placement_rate ?? "—"} sub="expected placement rate" icon={Briefcase} accent="bg-emerald-100 text-emerald-600" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <FunnelCard title="Placement Funnel" rows={funnel} />
        <FunnelCard title="Salary Distribution" rows={salary} />
        <FunnelCard title="Skill Demand" rows={skill} />
        <FunnelCard title="Department Comparison" rows={departments} />
      </div>
    </div>
  );
}
