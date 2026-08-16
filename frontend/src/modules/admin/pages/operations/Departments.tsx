import { useQuery } from "@tanstack/react-query";
import { Building2 } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

export function AdminDepartments() {
  const token = useAuthStore((s) => s.token);
  const depts = useQuery({ queryKey: ["admin-depts"], queryFn: () => adminApi.departments(token!), enabled: !!token });
  const d = depts.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Department Management"
        subtitle="Program-wise student health, performance and placement"
        icon={Building2}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Departments" value={d?.count} sub="with student records" icon={Building2} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Programs" value={d?.all_programs.length} sub="full program list" icon={Building2} accent="bg-violet-100 text-violet-600" />
        <StatCard label="Students" value={d?.departments.reduce((a, b) => a + b.students, 0) ?? d?.departments.length} icon={Building2} accent="bg-emerald-100 text-emerald-600" />
        <StatCard label="Avg pass rate" value={d?.departments.length ? `${Math.round((d.departments.reduce((a, b) => a + b.pass_rate, 0) / d.departments.length) * 10) / 10}%` : "—"} icon={Building2} accent="bg-amber-100 text-amber-600" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Departments</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th className="pb-2">Program</th>
                <th className="pb-2 text-right">Students</th>
                <th className="pb-2 text-right">GPA</th>
                <th className="pb-2 text-right">Attendance</th>
                <th className="pb-2 text-right">Pass</th>
                <th className="pb-2 text-right">Failure</th>
                <th className="pb-2 text-right">Readiness</th>
                <th className="pb-2 text-right">Placement</th>
                <th className="pb-2 text-right">Health</th>
              </tr>
            </thead>
            <tbody>
              {(d?.departments ?? []).map((row) => (
                <tr key={row.program} className="border-b border-[var(--border)]">
                  <td className="py-2 font-medium">
                    <span className="line-clamp-1 max-w-[220px]">{row.program}</span>
                    {row.flag && <span className="text-xs font-semibold text-red-600">⚑ {row.flag}</span>}
                  </td>
                  <td className="py-2 text-right">{row.students}</td>
                  <td className="py-2 text-right">{row.avg_gpa}</td>
                  <td className="py-2 text-right">{row.attendance}%</td>
                  <td className="py-2 text-right">{row.pass_rate}%</td>
                  <td className="py-2 text-right text-red-600">{row.failure_rate}%</td>
                  <td className="py-2 text-right">{row.avg_readiness}</td>
                  <td className="py-2 text-right">{row.placement}%</td>
                  <td className="py-2 text-right font-semibold">{row.health}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
