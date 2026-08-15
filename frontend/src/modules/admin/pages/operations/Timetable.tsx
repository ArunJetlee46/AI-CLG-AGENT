import { useMutation, useQuery } from "@tanstack/react-query";
import { CalendarClock, CheckCircle2, Save, TriangleAlert, Zap } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi, type TimetableOptimizeResult } from "@/modules/admin/api";

export function AdminTimetable() {
  const token = useAuthStore((s) => s.token);
  const [commit, setCommit] = useState(false);
  const [result, setResult] = useState<TimetableOptimizeResult | null>(null);

  const conflicts = useQuery({ queryKey: ["admin-timetable"], queryFn: () => adminApi.timetableConflicts(token!), enabled: !!token });

  const optimize = useMutation({
    mutationFn: () => adminApi.optimizeTimetable({ commit, start_hour: 9, end_hour: 17, slot_minutes: 60 }, token!),
    onSuccess: setResult,
  });

  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="AI Timetable Optimization"
        subtitle="Generate a conflict-free schedule from courses, rooms and lecturers"
        icon={CalendarClock}
        actions={
          <Button variant="outline" disabled={optimize.isPending} onClick={() => optimize.mutate()}>
            <Zap className="h-4 w-4" /> {commit ? "Generate & Commit" : "Generate Proposal"}
          </Button>
        }
      />

      <label className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
        <input type="checkbox" checked={commit} onChange={(e) => setCommit(e.target.value === "on" ? true : e.target.checked)} />
        Commit to timetable (requires AI execution enabled)
      </label>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-5">
        <StatCard label="Existing conflicts" value={conflicts.data?.count} sub={`${conflicts.data?.total_entries ?? 0} entries analyzed`} icon={TriangleAlert} accent="bg-red-100 text-red-600" />
        <StatCard label="Courses scheduled" value={result?.stats.courses_scheduled} icon={CheckCircle2} accent="bg-green-100 text-green-600" />
        <StatCard label="Unassigned" value={result?.stats.courses_unassigned} icon={TriangleAlert} accent="bg-amber-100 text-amber-600" />
        <StatCard label="Room utilization" value={result ? `${result.stats.room_utilization}%` : null} icon={CalendarClock} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Conflicts before" value={result?.conflicts_before} sub="proposal targets zero" icon={Zap} accent="bg-violet-100 text-violet-600" />
      </div>

      {conflicts.data && conflicts.data.count > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TriangleAlert className="h-4 w-4 text-red-500" /> Detected conflicts ({conflicts.data.count})
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {conflicts.data.conflicts.slice(0, 20).map((c, i) => (
              <div key={i} className="flex flex-wrap items-center gap-2 border-b border-[var(--border)] pb-2 text-sm">
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${c.type === "room" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                  {c.type}
                </span>
                <span className="text-[var(--muted-foreground)]">{c.day} {c.start}–{c.end}</span>
                <span>{c.first}</span>
                <span className="text-[var(--muted-foreground)]">×</span>
                <span>{c.second}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Proposed schedule ({result.proposed.length} classes)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                    <th className="pb-2">Course</th>
                    <th className="pb-2">Room</th>
                    <th className="pb-2">Lecturer</th>
                    <th className="pb-2">Day</th>
                    <th className="pb-2">Time</th>
                    <th className="pb-2 text-right">Enrolled</th>
                    <th className="pb-2 text-right">Capacity</th>
                  </tr>
                </thead>
                <tbody>
                  {result.proposed.map((p) => (
                    <tr key={`${p.course_code}-${p.day}-${p.start}`} className="border-b border-[var(--border)]">
                      <td className="py-2">
                        <span className="font-mono text-xs font-medium">{p.course_code}</span>
                      </td>
                      <td className="py-2 font-mono text-xs">{p.room_no}</td>
                      <td className="py-2 font-mono text-xs">{p.staff_id}</td>
                      <td className="py-2">{p.day}</td>
                      <td className="py-2">{p.start}–{p.end}</td>
                      <td className="py-2 text-right">{p.enrolled}</td>
                      <td className="py-2 text-right">{p.capacity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {result.stats.unassigned.length > 0 && (
              <p className="mt-3 text-xs text-[var(--muted-foreground)]">
                {result.stats.unassigned.length} course(s) could not be placed.
              </p>
            )}
            {result.commit && (
              <p className="mt-3 flex items-center gap-1 text-xs font-semibold text-green-700">
                <Save className="h-3.5 w-3.5" /> Committed and audit-logged.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {days.map((day) => (
        result && result.proposed.filter((p) => p.day === day).length > 0 && (
          <div key={day} className="rounded-xl border border-[var(--border)] bg-white/60 p-4">
            <p className="mb-2 text-sm font-semibold">{day}</p>
            <div className="flex flex-wrap gap-2">
              {result.proposed
                .filter((p) => p.day === day)
                .map((p) => (
                  <span key={`${p.course_code}-${p.start}`} className="rounded-lg bg-[var(--primary)]/10 px-2 py-1 text-xs font-medium text-[var(--primary)]">
                    {p.start} {p.course_code} · {p.room_no}
                  </span>
                ))}
            </div>
          </div>
        )
      ))}
    </div>
  );
}
