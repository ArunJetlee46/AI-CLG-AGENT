import { useQuery } from "@tanstack/react-query";
import { FileBarChart, FileText } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { facultyApi } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";

const bandTone = (band: string) => (band === "healthy" || band === "strong" ? "success" : band === "warning" ? "warning" : "destructive");

export function CourseReports() {
  const token = useAuthStore((s) => s.token);
  const [code, setCode] = useState("");

  const profile = useQuery({ queryKey: ["fac-profile"], queryFn: () => facultyApi.me(token!), enabled: !!token });
  const report = useQuery({
    queryKey: ["fac-report", code],
    queryFn: () => facultyApi.courseReport(code, token!),
    enabled: !!token && code !== "",
  });

  const course = profile.data?.courses.find((c: { course_code: string }) => c.course_code === code);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Course Reports" subtitle="Auto-generated analytical reports per course" icon={FileBarChart} accent="bg-amber-100 text-amber-600" />

      <div className="flex flex-wrap items-center gap-2">
        {profile.data?.courses.map((c: { course_code: string }) => (
          <button
            key={c.course_code}
            onClick={() => setCode(c.course_code)}
            className={`rounded-full border px-3 py-1 text-sm transition-colors ${code === c.course_code ? "border-[var(--primary)] bg-[var(--primary)]/10 font-medium text-[var(--primary)]" : "border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]"}`}
          >
            {c.course_code}
          </button>
        ))}
        {!profile.data?.courses.length && <p className="text-sm text-[var(--muted-foreground)]">No courses linked to you yet.</p>}
      </div>

      {report.data && (
        <div className="flex flex-col gap-4">
          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <FileText className="h-4 w-4" />
                {report.data.course_code} — {report.data.course_title}
                <Badge tone={bandTone(report.data.band)} className="ml-auto">
                  {report.data.band} · health {report.data.health_score ?? "—"}/100
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {[
                  { label: "Enrolled", value: report.data.enrolled },
                  { label: "Attendance", value: `${Math.round(report.data.attendance * 100)}%` },
                  { label: "Pass rate", value: `${Math.round(report.data.pass_rate * 100)}%` },
                  { label: "At risk", value: report.data.at_risk_students.length },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/40 px-3 py-2">
                    <div className="text-[11px] text-[var(--muted-foreground)]">{label}</div>
                    <div className="text-lg font-semibold">{value}</div>
                  </div>
                ))}
              </div>

              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Grade distribution</p>
                <div className="flex h-3 overflow-hidden rounded-full bg-[var(--muted)]">
                  {([
                    ["outstanding", "bg-emerald-500"],
                    ["good", "bg-sky-500"],
                    ["average", "bg-amber-500"],
                    ["below", "bg-red-500"],
                  ] as const).map(([key, cls]) => (
                    <div key={key} className={cls} style={{ width: `${(report.data.distribution[key] / Math.max(report.data.enrolled, 1)) * 100}%` }} />
                  ))}
                </div>
                <div className="mt-1 flex flex-wrap gap-3 text-xs text-[var(--muted-foreground)]">
                  {([
                    ["outstanding", "bg-emerald-500"],
                    ["good", "bg-sky-500"],
                    ["average", "bg-amber-500"],
                    ["below", "bg-red-500"],
                  ] as const).map(([key, cls]) => (
                    <span key={key} className="flex items-center gap-1">
                      <span className={`h-2 w-2 rounded-full ${cls}`} /> {key}: {report.data.distribution[key]}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Top students</p>
                <div className="flex flex-wrap gap-2">
                  {report.data.top_students.map((s) => (
                    <span key={s} className="rounded-full border border-[var(--border)] px-2.5 py-0.5 font-mono text-xs">{s}</span>
                  ))}
                </div>
              </div>

              {report.data.at_risk_students.length > 0 && (
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-red-600">At-risk students</p>
                  <div className="flex flex-col gap-1.5">
                    {report.data.at_risk_students.map((s) => (
                      <div key={s.student_id} className="flex items-center justify-between rounded-md border border-[var(--border)] px-3 py-1.5 text-sm">
                        <span className="font-mono">{s.student_id}</span>
                        <Badge tone={bandTone(s.risk_level)}>{s.risk_level}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="rounded-lg border-l-4 border-[var(--primary)] bg-[var(--primary)]/5 px-3 py-2">
                <p className="text-sm leading-relaxed">{report.data.narrative}</p>
                <p className="mt-1 text-xs text-[var(--muted-foreground)]">Generated {report.data.generated_on}</p>
              </div>

              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Key drivers</p>
                <ul className="list-inside list-disc text-sm text-[var(--muted-foreground)]">
                  {report.data.drivers.map((d) => <li key={d}>{d}</li>)}
                </ul>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {!report.data && code && <p className="text-sm text-[var(--muted-foreground)]">{course ? "Generating report…" : "No data for this course."}</p>}
    </div>
  );
}
