import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { AlertTriangle, BookOpen, ClipboardList, HeartPulse, TrendingDown, Users } from "lucide-react";

import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { facultyApi, type AtRiskStudent, type CourseHealth, type InterventionProposal } from "@/modules/faculty/api";
import { cn } from "@/core/lib/utils";
import { useAuthStore } from "@/core/stores/auth";

const riskBg = (level: string) =>
  level === "high"
    ? "bg-red-50 border-red-200 text-red-700"
    : level === "medium"
      ? "bg-amber-50 border-amber-200 text-amber-700"
      : "bg-green-50 border-green-200 text-green-700";

const healthColor = (band: string) =>
  band === "healthy" ? "text-green-600" : band === "warning" ? "text-amber-600" : "text-red-600";

export function FacultyDashboard() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const me = useQuery({ queryKey: ["faculty-me"], queryFn: () => facultyApi.me(token!), enabled: !!token });
  const overview = useQuery({ queryKey: ["faculty-overview"], queryFn: () => facultyApi.overview(token!), enabled: !!token });
  const atRisk = useQuery({ queryKey: ["faculty-at-risk"], queryFn: () => facultyApi.atRisk(token!), enabled: !!token });
  const interventions = useQuery({ queryKey: ["faculty-interventions"], queryFn: () => facultyApi.interventions(token!), enabled: !!token });

  const [selectedCourse, setSelectedCourse] = useState("");
  const [health, setHealth] = useState<CourseHealth | null>(null);
  const [attendance, setAttendance] = useState<{ below_count: number; students: { student_id: string; attendance_rate: number }[] } | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const [studentId, setStudentId] = useState("");
  const [planText, setPlanText] = useState("");
  const [proposal, setProposal] = useState<InterventionProposal | null>(null);
  const [interventionBusy, setInterventionBusy] = useState(false);

  const runCourseDetail = async (courseCode: string) => {
    if (!token || !courseCode) return;
    setDetailBusy(true);
    try {
      setSelectedCourse(courseCode);
      const [h, a] = await Promise.all([
        facultyApi.courseHealth(courseCode, token),
        facultyApi.courseAttendance(courseCode, token),
      ]);
      setHealth(h);
      setAttendance(a);
    } finally {
      setDetailBusy(false);
    }
  };

  const propose = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !studentId.trim() || !selectedCourse || !planText.trim()) return;
    setInterventionBusy(true);
    try {
      setProposal(await facultyApi.proposeIntervention(studentId.trim().toUpperCase(), selectedCourse, planText.trim(), token));
      setPlanText("");
      queryClient.invalidateQueries({ queryKey: ["faculty-interventions"] });
    } finally {
      setInterventionBusy(false);
    }
  };

  const decide = async (id: string, decision: string) => {
    if (!token) return;
    try {
      await facultyApi.decide(id, decision, token);
      queryClient.invalidateQueries({ queryKey: ["faculty-interventions"] });
      queryClient.invalidateQueries({ queryKey: ["faculty-at-risk"] });
    } catch {
      // approval errors surface in the list reload
    }
  };

  const summary = overview.data?.summary;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Faculty Copilot"
        subtitle={me.data ? `${me.data.staff_id} · ${me.data.department} · ${me.data.course_count} courses · ${me.data.student_count} students` : "Loading..."}
        icon={Users}
        accent="bg-violet-100 text-violet-600"
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Students" value={me.data?.student_count} sub="across your courses" icon={Users} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Courses" value={me.data?.course_count} sub="in your workload" icon={BookOpen} accent="bg-violet-100 text-violet-600" />
        <StatCard label="At risk" value={summary?.at_risk} sub="high-risk flags" icon={AlertTriangle} accent="bg-red-100 text-red-600" />
        <StatCard label="Declining courses" value={overview.data?.trends.length} sub="negative attendance trend" icon={TrendingDown} accent="bg-amber-100 text-amber-600" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Class performance</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-md border border-[var(--border)] p-3">
                <div className="text-xs text-[var(--muted-foreground)]">Students</div>
                <div className="text-xl font-semibold">{summary?.students ?? "..."}</div>
              </div>
              <div className="rounded-md border border-[var(--border)] p-3">
                <div className="text-xs text-[var(--muted-foreground)]">Average</div>
                <div className="text-xl font-semibold">{summary?.average ?? "-"}</div>
              </div>
              <div className="rounded-md border border-[var(--border)] p-3">
                <div className="text-xs text-[var(--muted-foreground)]">Pass rate</div>
                <div className="text-xl font-semibold">
                  {summary ? `${Math.round(summary.pass_rate * 100)}%` : "-"}
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className={cn("rounded-full border px-2 py-0.5 text-xs font-medium", riskBg("low"))}>
                Strong: {summary?.strong ?? "..."}
              </span>
              <span className={cn("rounded-full border px-2 py-0.5 text-xs font-medium", riskBg("medium"))}>
                Average: {summary?.average_band ?? "..."}
              </span>
              <span className={cn("rounded-full border px-2 py-0.5 text-xs font-medium", riskBg("high"))}>
                At risk: {summary?.at_risk ?? "..."}
              </span>
            </div>
            {overview.data?.trends.map((trend) => (
              <div key={trend.course_code} className="rounded-md border border-l-4 border-l-amber-500 bg-amber-50 px-3 py-2 text-xs">
                {trend.detail}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Course health</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <select
              value={selectedCourse}
              onChange={(e) => runCourseDetail(e.target.value)}
              disabled={detailBusy}
              className="h-10 w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)]"
            >
              <option value="">Select a course...</option>
              {me.data?.courses.map((course) => (
                <option key={course.course_code} value={course.course_code}>
                  {course.course_code} - {course.title}
                </option>
              ))}
            </select>
            {health && health.health_score !== null && (
              <div className="flex flex-col gap-2">
                <div className="flex items-end gap-2">
                  <span className="text-4xl font-bold">{health.health_score}</span>
                  <span className="text-sm text-[var(--muted-foreground)]">/100</span>
                  <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", healthColor(health.band))}>
                    {health.band.toUpperCase()}
                  </span>
                </div>
                {health.drivers.map((driver) => (
                  <div key={driver} className="text-xs text-[var(--muted-foreground)]">
                    {driver}
                  </div>
                ))}
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex justify-between rounded-md border border-[var(--border)] px-3 py-2">
                    <span className="text-[var(--muted-foreground)]">Attendance</span>
                    <span className="font-medium">{Math.round(health.components.attendance * 100)}%</span>
                  </div>
                  <div className="flex justify-between rounded-md border border-[var(--border)] px-3 py-2">
                    <span className="text-[var(--muted-foreground)]">Failure rate</span>
                    <span className="font-medium">{Math.round(health.components.failure_rate * 100)}%</span>
                  </div>
                </div>
              </div>
            )}
            {attendance && (
              <div className="rounded-md border border-[var(--border)] bg-[var(--muted)] px-3 py-2 text-xs">
                <div className="font-medium">
                  {attendance.below_count} student(s) below the 75% attendance threshold
                </div>
                {attendance.students.slice(0, 8).map((s) => (
                  <div key={s.student_id} className="mt-1 flex justify-between">
                    <span>{s.student_id}</span>
                    <span className="font-medium text-red-600">{Math.round(s.attendance_rate * 100)}%</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>AI Risk Monitor</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                  <th className="py-2 pr-4">Student</th>
                  <th className="py-2 pr-4">Course</th>
                  <th className="py-2 pr-4">Risk</th>
                  <th className="py-2 pr-4">Probability</th>
                  <th className="py-2 pr-4">Reason</th>
                </tr>
              </thead>
              <tbody>
                {atRisk.data?.slice(0, 12).map((student: AtRiskStudent) => (
                  <tr key={`${student.student_id}-${student.course_code}`} className="border-b border-[var(--border)]">
                    <td className="py-2 pr-4 font-medium">{student.student_id}</td>
                    <td className="py-2 pr-4">{student.course_code}</td>
                    <td className="py-2 pr-4">
                      <span className={cn("rounded-full border px-2 py-0.5 text-xs font-medium", riskBg(student.risk_level))}>
                        {student.risk_level.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2 pr-4">{Math.round(student.probability * 100)}%</td>
                    <td className="py-2 pr-4 text-xs text-[var(--muted-foreground)]">{student.reasons.join(", ")}</td>
                  </tr>
                ))}
                {atRisk.data?.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-3 text-sm text-[var(--muted-foreground)]">
                      No at-risk students across your courses.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HeartPulse className="h-4 w-4" /> Propose an intervention
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <form onSubmit={propose} className="flex flex-col gap-3">
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                <Input
                  value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                  placeholder="Student ID, e.g. STU00012"
                  className="text-sm"
                  disabled={interventionBusy}
                />
                <select
                  value={selectedCourse}
                  onChange={(e) => setSelectedCourse(e.target.value)}
                  disabled={interventionBusy}
                  className="h-10 w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)]"
                >
                  <option value="">Course...</option>
                  {me.data?.courses.map((course) => (
                    <option key={course.course_code} value={course.course_code}>
                      {course.course_code}
                    </option>
                  ))}
                </select>
              </div>
              <Input
                value={planText}
                onChange={(e) => setPlanText(e.target.value)}
                placeholder='Plan, e.g. "Schedule a meeting, recommend Unit 2 revision, monitor attendance for 2 weeks."'
                className="text-sm"
                disabled={interventionBusy}
              />
              <Button type="submit" disabled={interventionBusy || !studentId.trim() || !selectedCourse || !planText.trim()}>
                {interventionBusy ? "Submitting..." : "Propose for approval"}
              </Button>
            </form>
            {proposal && (
              <div className="rounded-md border border-l-4 border-l-green-500 bg-green-50 px-3 py-2 text-xs">
                <div className="font-medium">{proposal.message}</div>
                <div>Approval request: {proposal.approval_id.slice(0, 8)} - {proposal.status}</div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardList className="h-4 w-4" /> My interventions
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {interventions.data?.length === 0 && (
              <p className="text-sm text-[var(--muted-foreground)]">No interventions proposed yet.</p>
            )}
            {interventions.data?.map((row) => (
              <div key={row.id} className="rounded-md border border-[var(--border)] px-3 py-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium">
                    {row.student_id} - {row.course_code}
                  </span>
                  <span
                    className={cn(
                      "rounded-full border px-2 py-0.5 font-medium",
                      row.status === "approved"
                        ? "border-green-200 bg-green-50 text-green-700"
                        : row.status === "rejected"
                          ? "border-red-200 bg-red-50 text-red-700"
                          : "border-amber-200 bg-amber-50 text-amber-700"
                    )}
                  >
                    {row.status}
                  </span>
                </div>
                <div className="mt-1 text-[var(--muted-foreground)]">{row.plan_text}</div>
                {row.status === "pending" && (
                  <div className="mt-2 flex gap-2">
                    <Button size="sm" variant="default" onClick={() => decide(row.id, "approve")}>
                      Approve
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => decide(row.id, "reject")}>
                      Reject
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
