import { useQuery } from "@tanstack/react-query";
import { GraduationCap } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

const bandStyles: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-red-100 text-red-700",
};

export function AdminStudentAnalytics() {
  const token = useAuthStore((s) => s.token);
  const q = useQuery({ queryKey: ["admin-students"], queryFn: () => adminApi.studentAnalytics(token!), enabled: !!token });
  const d = q.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Student Analytics" subtitle="Academic performance, risk bands and program trends" icon={GraduationCap} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Students" value={d?.total} icon={GraduationCap} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Avg attendance" value={d ? `${d.avg_attendance}%` : null} icon={GraduationCap} accent="bg-emerald-100 text-emerald-600" />
        <StatCard label="Avg GPA" value={d?.avg_gpa} icon={GraduationCap} accent="bg-violet-100 text-violet-600" />
        <StatCard label="Avg marks" value={d?.avg_marks} icon={GraduationCap} accent="bg-amber-100 text-amber-600" />
        <StatCard label="Pass rate" value={d ? `${d.pass_rate}%` : null} icon={GraduationCap} accent="bg-indigo-100 text-indigo-600" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Risk Bands</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {[
              { label: "Low risk", v: d?.risk_bands.low, cls: "bg-green-500" },
              { label: "Medium risk", v: d?.risk_bands.medium, cls: "bg-amber-500" },
              { label: "High risk", v: d?.risk_bands.high, cls: "bg-red-500" },
            ].map((r) => (
              <div key={r.label} className="flex items-center gap-2 text-sm">
                <span className="w-28">{r.label}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                  <span className={`block h-full rounded-full ${r.cls}`} style={{ width: `${d?.total ? ((r.v ?? 0) / d.total) * 100 : 0}%` }} />
                </span>
                <span className="w-8 text-right">{r.v ?? 0}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>By Year</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {(d?.by_year ?? []).map((y) => (
              <div key={y.year} className="flex items-center gap-2 border-b border-[var(--border)] pb-2 text-sm">
                <span className="w-24">Year {y.year}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                  <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${d?.total ? (y.count / d.total) * 100 : 0}%` }} />
                </span>
                <span className="text-xs text-[var(--muted-foreground)]">{y.count} · {y.at_risk} at risk</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Top performers</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th className="pb-2">Student</th>
                <th className="pb-2">Program</th>
                <th className="pb-2 text-right">GPA</th>
                <th className="pb-2 text-right">Readiness</th>
                <th className="pb-2">Band</th>
              </tr>
            </thead>
            <tbody>
              {(d?.top_students ?? []).map((s) => (
                <tr key={s.student_id} className="border-b border-[var(--border)]">
                  <td className="py-2 font-mono text-xs">{s.student_id}</td>
                  <td className="py-2"><span className="line-clamp-1 max-w-[220px]">{s.program}</span></td>
                  <td className="py-2 text-right font-semibold text-green-600">{s.gpa}</td>
                  <td className="py-2 text-right">{s.readiness_score}</td>
                  <td className="py-2"><span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${bandStyles[s.band] ?? ""}`}>{s.band.toUpperCase()}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>At-risk students</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th className="pb-2">Student</th>
                <th className="pb-2">Program</th>
                <th className="pb-2 text-right">GPA</th>
                <th className="pb-2 text-right">Readiness</th>
                <th className="pb-2">Band</th>
              </tr>
            </thead>
            <tbody>
              {(d?.bottom_students ?? []).map((s) => (
                <tr key={s.student_id} className="border-b border-[var(--border)]">
                  <td className="py-2 font-mono text-xs">{s.student_id}</td>
                  <td className="py-2"><span className="line-clamp-1 max-w-[220px]">{s.program}</span></td>
                  <td className="py-2 text-right">{s.gpa}</td>
                  <td className="py-2 text-right">{s.readiness_score}</td>
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
