import { useQuery } from "@tanstack/react-query";
import { TrendingUp } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

export function AdminEnrollmentForecast() {
  const token = useAuthStore((s) => s.token);
  const q = useQuery({ queryKey: ["admin-forecast"], queryFn: () => adminApi.enrollmentForecast(token!), enabled: !!token });
  const d = q.data;
  const series = [...(d?.historical ?? []), ...(d?.forecast ?? [])];
  const forecastYears = new Set((d?.forecast ?? []).map((f) => f.year));
  const max = Math.max(1, ...series.map((s) => s.enrollments));
  const currentYear = new Date().getFullYear();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Enrollment Forecast" subtitle="Historical trends and predicted intake" icon={TrendingUp} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard label="Total enrollments" value={d?.total_enrollments} icon={TrendingUp} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Current year" value={d?.current_enrollments} sub={`${currentYear}`} icon={TrendingUp} accent="bg-violet-100 text-violet-600" />
        <StatCard label="Next year (forecast)" value={d?.forecast.find((f) => f.year === currentYear + 1)?.enrollments} icon={TrendingUp} accent="bg-emerald-100 text-emerald-600" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Enrollment trend & forecast</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-48 items-end gap-3 overflow-x-auto pb-1">
            {series.map((s) => (
              <div key={s.year} className="flex min-w-12 flex-col items-center gap-1">
                <span className="text-xs font-semibold">{s.enrollments}</span>
                <div
                  className={`w-full rounded-t-lg ${forecastYears.has(s.year) ? "bg-[var(--primary)]/40" : "bg-[var(--primary)]"}`}
                  style={{ height: `${Math.max(4, (s.enrollments / max) * 160)}px` }}
                />
                <span className="text-xs text-[var(--muted-foreground)]">
                  {s.year}{forecastYears.has(s.year) ? "·" : ""}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-[var(--muted-foreground)]">Shaded bars are forecast years.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>By department</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {(d?.by_department ?? []).map((r) => (
            <div key={r.department} className="flex items-center gap-2 border-b border-[var(--border)] pb-2 text-sm">
              <span className="w-56 truncate">{r.department}</span>
              <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${(r.enrollments / Math.max(1, d?.total_enrollments ?? 1)) * 100}%` }} />
              </span>
              <span className="w-10 text-right">{r.enrollments}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
