import { useQuery } from "@tanstack/react-query";
import { UserX } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

const bandStyles: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-green-100 text-green-700",
};

export function AdminDropoutAnalytics() {
  const token = useAuthStore((s) => s.token);
  const q = useQuery({ queryKey: ["admin-dropout"], queryFn: () => adminApi.dropoutAnalytics(token!), enabled: !!token });
  const d = q.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Dropout Risk Analytics" subtitle="ML-predicted attrition and intervention targets" icon={UserX} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Students" value={d?.total} icon={UserX} accent="bg-sky-100 text-sky-600" />
        <StatCard label="High risk" value={d?.bands.high} icon={UserX} accent="bg-red-100 text-red-600" />
        <StatCard label="Medium risk" value={d?.bands.medium} icon={UserX} accent="bg-amber-100 text-amber-600" />
        <StatCard label="High-risk ratio" value={d ? `${(d.high_risk_ratio * 100).toFixed(1)}%` : null} icon={UserX} accent="bg-violet-100 text-violet-600" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Risk Drivers</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {[
              { label: "Avg attendance", v: d?.drivers.avg_attendance },
              { label: "Avg GPA", v: d?.drivers.avg_gpa },
              { label: "Avg backlogs", v: d?.drivers.avg_backlogs },
            ].map((r) => (
              <div key={r.label} className="flex items-center gap-2 text-sm">
                <span className="w-36">{r.label}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                  <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${Math.min(100, (r.v ?? 0) * 20)}%` }} />
                </span>
                <span className="w-10 text-right">{r.v ?? 0}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>By Program</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {(d?.by_program ?? []).map((p) => (
              <div key={p.program} className="flex items-center gap-2 border-b border-[var(--border)] pb-2 text-sm">
                <span className="w-52 truncate">{p.program}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                  <span className="block h-full rounded-full bg-red-500" style={{ width: `${(p.high_risk / Math.max(1, p.count)) * 100}%` }} />
                </span>
                <span className="text-xs text-[var(--muted-foreground)]">{p.count} · {p.high_risk} high</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Highest dropout risk</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th className="pb-2">Student</th>
                <th className="pb-2">Program</th>
                <th className="pb-2 text-right">GPA</th>
                <th className="pb-2 text-right">Attendance</th>
                <th className="pb-2 text-right">Backlogs</th>
                <th className="pb-2 text-right">Risk</th>
                <th className="pb-2">Band</th>
              </tr>
            </thead>
            <tbody>
              {(d?.top_risk ?? []).map((s) => (
                <tr key={s.student_id} className="border-b border-[var(--border)]">
                  <td className="py-2 font-mono text-xs">{s.student_id}</td>
                  <td className="py-2"><span className="line-clamp-1 max-w-[200px]">{s.program}</span></td>
                  <td className="py-2 text-right">{s.gpa}</td>
                  <td className="py-2 text-right">{s.attendance_rate}%</td>
                  <td className="py-2 text-right">{s.backlogs}</td>
                  <td className="py-2 text-right font-semibold text-red-600">{s.dropout_risk}%</td>
                  <td className="py-2"><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${bandStyles[s.band] ?? ""}`}>{s.band.toUpperCase()}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
