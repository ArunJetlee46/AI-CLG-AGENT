import { useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

export function AdminCurriculumIntelligence() {
  const token = useAuthStore((s) => s.token);
  const q = useQuery({ queryKey: ["admin-curriculum"], queryFn: () => adminApi.curriculum(token!), enabled: !!token });
  const d = q.data;
  const difficult = d?.difficult_courses ?? [];
  const gaps = d?.prerequisite_health ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Curriculum Intelligence" subtitle="Difficulty flags and prerequisite health analysis" icon={BookOpen} />

      <StatCard label="Courses analyzed" value={d?.total_courses} icon={BookOpen} accent="bg-sky-100 text-sky-600" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Difficult courses ({difficult.filter((c) => c.difficult).length})</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                  <th className="pb-2">Course</th>
                  <th className="pb-2 text-right">Enrolled</th>
                  <th className="pb-2 text-right">Avg marks</th>
                  <th className="pb-2 text-right">Failure</th>
                  <th className="pb-2">Flag</th>
                </tr>
              </thead>
              <tbody>
                {difficult.map((c) => (
                  <tr key={c.course_code} className="border-b border-[var(--border)]">
                    <td className="py-2">
                      <span className="font-mono text-xs font-medium">{c.course_code}</span>
                      <p className="line-clamp-1 max-w-[240px] text-xs text-[var(--muted-foreground)]">{c.title}</p>
                    </td>
                    <td className="py-2 text-right">{c.enrolled}</td>
                    <td className="py-2 text-right">{c.avg_marks}</td>
                    <td className="py-2 text-right text-red-600">{c.failure_rate}%</td>
                    <td className="py-2">
                      {c.difficult ? (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">DIFFICULT</span>
                      ) : (
                        <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">OK</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Prerequisite health</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                  <th className="pb-2">Course</th>
                  <th className="pb-2">Prereq</th>
                  <th className="pb-2 text-right">Gap</th>
                  <th className="pb-2">Health</th>
                </tr>
              </thead>
              <tbody>
                {gaps.map((g) => (
                  <tr key={`${g.course_code}-${g.prerequisite}`} className="border-b border-[var(--border)]">
                    <td className="py-2 font-mono text-xs">{g.course_code}</td>
                    <td className="py-2 font-mono text-xs text-[var(--muted-foreground)]">{g.prerequisite}</td>
                    <td className="py-2 text-right font-semibold">{g.gap}</td>
                    <td className="py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${g.healthy ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                        {g.healthy ? "HEALTHY" : "GAP"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
