import { useQuery } from "@tanstack/react-query";
import { Users } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

export function AdminFacultyAnalytics() {
  const token = useAuthStore((s) => s.token);
  const q = useQuery({ queryKey: ["admin-faculty"], queryFn: () => adminApi.facultyAnalytics(token!), enabled: !!token });
  const d = q.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Faculty Analytics" subtitle="Workload, utilization and per-faculty student outcomes" icon={Users} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Faculty" value={d?.summary.total_faculty} icon={Users} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Avg courses" value={d?.summary.avg_courses} icon={Users} accent="bg-violet-100 text-violet-600" />
        <StatCard label="Avg hours" value={d?.summary.avg_hours} icon={Users} accent="bg-emerald-100 text-emerald-600" />
        <StatCard label="Overloaded" value={d?.summary.overloaded} sub="flagged for intervention" icon={Users} accent="bg-red-100 text-red-600" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Faculty workload & outcomes</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th className="pb-2">Staff</th>
                <th className="pb-2">Department</th>
                <th className="pb-2 text-right">Courses</th>
                <th className="pb-2 text-right">Students</th>
                <th className="pb-2 text-right">Hours</th>
                <th className="pb-2 text-right">Utilization</th>
                <th className="pb-2 text-right">Pass rate</th>
                <th className="pb-2">Flag</th>
              </tr>
            </thead>
            <tbody>
              {(d?.rows ?? []).map((r) => (
                <tr key={r.staff_id} className="border-b border-[var(--border)]">
                  <td className="py-2 font-mono text-xs font-medium">{r.staff_id}</td>
                  <td className="py-2"><span className="line-clamp-1 max-w-[200px]">{r.department}</span></td>
                  <td className="py-2 text-right">{r.course_count}</td>
                  <td className="py-2 text-right">{r.student_count}</td>
                  <td className="py-2 text-right">{r.teaching_hours}</td>
                  <td className="py-2 text-right">{r.utilization}%</td>
                  <td className="py-2 text-right">{r.avg_pass_rate != null ? `${r.avg_pass_rate}%` : "—"}</td>
                  <td className="py-2 text-xs font-semibold text-red-600">{r.flag ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
