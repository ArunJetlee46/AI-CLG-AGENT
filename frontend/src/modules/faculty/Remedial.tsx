import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck, LifeBuoy } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { facultyApi, type RemedialPlan } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";

const bandTone = (band: string) => (band === "high" ? "destructive" : band === "medium" ? "warning" : "success");

const stepTone = (kind: string) => (kind === "attendance" ? "warning" : "primary");

export function Remedial() {
  const token = useAuthStore((s) => s.token);
  const [courseCode, setCourseCode] = useState("");
  const [studentId, setStudentId] = useState("");
  const [plan, setPlan] = useState<RemedialPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [proposed, setProposed] = useState<string | null>(null);

  const profile = useQuery({ queryKey: ["fac-profile"], queryFn: () => facultyApi.me(token!), enabled: !!token }).data;

  const generate = async () => {
    setError("");
    setProposed(null);
    if (!courseCode || !studentId.trim()) {
      setError("Pick a course and enter a student ID.");
      return;
    }
    setLoading(true);
    try {
      setPlan(await facultyApi.remedialPlan(courseCode, studentId.trim().toUpperCase(), token!));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate plan");
    } finally {
      setLoading(false);
    }
  };

  const propose = async () => {
    if (!plan) return;
    const planText = `Auto-generated remedial plan [${plan.risk_level ?? "medium"} risk]: ${plan.steps
      ?.map((s) => s.action)
      .join("; ")} Review in ${plan.review_after_days ?? 14} days.`;
    const res = await facultyApi.proposeIntervention(studentId.trim().toUpperCase(), courseCode, planText, token!);
    setProposed(res.message);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Remedial Plans" subtitle="Generate structured remediation for struggling students" icon={LifeBuoy} accent="bg-emerald-100 text-emerald-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm">Select student</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {profile?.courses.map((c: { course_code: string }) => (
              <button
                key={c.course_code}
                onClick={() => setCourseCode(c.course_code)}
                className={`rounded-full border px-3 py-1 text-sm transition-colors ${courseCode === c.course_code ? "border-[var(--primary)] bg-[var(--primary)]/10 font-medium text-[var(--primary)]" : "border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]"}`}
              >
                {c.course_code}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              placeholder="Student ID (e.g. BCS2301)"
              className="h-10 w-56 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm outline-none focus:border-[var(--primary)]"
            />
            <Button type="button" onClick={generate} disabled={loading}>
              {loading ? "Generating…" : "Generate plan"}
            </Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {plan && !plan.exists && (
        <Card className="card-shell">
          <CardContent className="text-sm text-[var(--muted-foreground)]">{plan.detail ?? "No plan available."}</CardContent>
        </Card>
      )}

      {plan?.exists && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
              <ClipboardCheck className="h-4 w-4" />
              {plan.course_code} — {plan.course_title}
              <Badge tone={bandTone(plan.risk_level ?? "")} className="ml-auto">
                {plan.risk_level} risk · {Math.round((plan.probability ?? 0) * 100)}%
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-3 text-sm">
              <span className="rounded-full border border-[var(--border)] px-2.5 py-0.5 font-mono">{plan.student_id}</span>
              <span className="rounded-full border border-[var(--border)] px-2.5 py-0.5">GPA {plan.profile?.gpa}</span>
              <span className="rounded-full border border-[var(--border)] px-2.5 py-0.5">Attendance {Math.round((plan.profile?.attendance_rate ?? 0) * 100)}%</span>
              <span className="rounded-full border border-[var(--border)] px-2.5 py-0.5">Marks {plan.profile?.marks ?? "—"} ({plan.profile?.grade})</span>
            </div>
            <div className="flex flex-col gap-2">
              {plan.steps?.map((s) => (
                <div key={s.action} className="rounded-lg border border-[var(--border)] p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium capitalize">{s.kind}</span>
                    <Badge tone={stepTone(s.kind)}>{s.priority}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-[var(--muted-foreground)]">{s.action}</p>
                  <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">Metric: {s.metric}</p>
                </div>
              ))}
            </div>
            <p className="text-xs text-[var(--muted-foreground)]">Review progress after {plan.review_after_days} days.</p>
            <div className="flex flex-wrap items-center gap-3">
              <Button type="button" size="sm" onClick={propose}>Propose as intervention</Button>
              {proposed && <span className="text-sm text-[var(--primary)]">{proposed}</span>}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
