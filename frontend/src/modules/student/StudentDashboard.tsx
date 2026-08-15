import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  BookOpen,
  CalendarCheck,
  ClipboardList,
  Compass,
  FileText,
  GraduationCap,
  Rocket,
  Sparkles,
  TrendingUp,
  Trophy,
  Users,
} from "lucide-react";

import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { studentApi, type AdviseResponse, type TodayPlan } from "@/modules/student/api";
import { cn } from "@/core/lib/utils";
import { useAuthStore } from "@/core/stores/auth";

const riskColor = (level: string) =>
  level === "high" ? "text-red-600" : level === "medium" ? "text-amber-600" : "text-green-600";

const severityBg = (severity: string) =>
  severity === "high"
    ? "border-l-red-500 bg-red-50"
    : severity === "medium"
      ? "border-l-amber-500 bg-amber-50"
      : "border-l-green-500 bg-green-50";

export function StudentDashboard() {
  const token = useAuthStore((s) => s.token);
  const username = useAuthStore((s) => s.username);

  const profile = useQuery({ queryKey: ["me"], queryFn: () => studentApi.profile(token!), enabled: !!token });
  const score = useQuery({ queryKey: ["me-score"], queryFn: () => studentApi.successScore(token!), enabled: !!token });
  const alerts = useQuery({ queryKey: ["me-alerts"], queryFn: () => studentApi.alerts(token!), enabled: !!token });
  const predictions = useQuery({ queryKey: ["me-predictions"], queryFn: () => studentApi.predictions(token!), enabled: !!token });

  const [courseCode, setCourseCode] = useState("");
  const [today, setToday] = useState<TodayPlan | null>(null);
  const [advice, setAdvice] = useState<AdviseResponse | null>(null);
  const [advisorBusy, setAdvisorBusy] = useState(false);

  const runToday = async () => {
    if (!token) return;
    setAdvisorBusy(true);
    try {
      setToday(await studentApi.today(token));
      setAdvice(null);
    } finally {
      setAdvisorBusy(false);
    }
  };

  const runAdvise = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !courseCode.trim()) return;
    setAdvisorBusy(true);
    try {
      setAdvice(await studentApi.advise(courseCode.trim().toUpperCase(), token));
      setToday(null);
    } finally {
      setAdvisorBusy(false);
    }
  };

  const plan = today?.plan ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Student Copilot"
        subtitle={`Welcome back, ${username}. Here is your academic picture at a glance.`}
        icon={GraduationCap}
        accent="bg-sky-100 text-sky-600"
        actions={
          profile.data && (
            <Badge tone="neutral" className="font-mono">
              {profile.data.student_id} · {profile.data.program}
            </Badge>
          )
        }
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { to: "/student/insights", label: "My Insights", sub: "Digital twin · progress", icon: TrendingUp, accent: "text-violet-600 bg-violet-100" },
          { to: "/student/community", label: "Community", sub: "Study partners · badges", icon: Trophy, accent: "text-amber-600 bg-amber-100" },
          { to: "/student/exam-prep", label: "Exam Prep", sub: "Practice quizzes", icon: BookOpen, accent: "text-teal-600 bg-teal-100" },
          { to: "/student/assignment-assistant", label: "Assignments", sub: "Plan · hints · rubric", icon: ClipboardList, accent: "text-indigo-600 bg-indigo-100" },
          { to: "/student/mock-interview", label: "Mock Interview", sub: "Scored practice", icon: Users, accent: "text-fuchsia-600 bg-fuchsia-100" },
          { to: "/student/resume-ats", label: "Resume ATS", sub: "Score your resume", icon: FileText, accent: "text-rose-600 bg-rose-100" },
          { to: "/student/project-mentor", label: "Project Mentor", sub: "Milestones & blockers", icon: Rocket, accent: "text-orange-600 bg-orange-100" },
          { to: "/chat?q=How%20do%20I%20register%20for%20a%20course%3F", label: "AI Curriculum Tutor", sub: "Ask the RAG tutor", icon: Compass, accent: "text-sky-600 bg-sky-100" },
        ].map(({ to, label, sub, icon: Icon, accent }) => (
          <Link
            key={to}
            to={to}
            className="card-shell flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3"
          >
            <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${accent}`}>
              <Icon className="h-4 w-4" />
            </span>
            <span className="min-w-0 leading-tight">
              <span className="block truncate text-sm font-semibold">{label}</span>
              <span className="block truncate text-xs text-[var(--muted-foreground)]">{sub}</span>
            </span>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" /> Student Success Score
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-end gap-3">
              <span className="text-5xl font-bold">{score.data?.success_score ?? "..."}</span>
              <span className="text-lg text-[var(--muted-foreground)]">/100</span>
              {score.data && (
                <Badge tone={score.data.risk_level === "high" ? "destructive" : score.data.risk_level === "medium" ? "warning" : "success"}>
                  {score.data.risk_level.toUpperCase()} RISK
                </Badge>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              {score.data?.components.map((c) => (
                <div key={c.name} className="text-sm">
                  <div className="flex justify-between">
                    <span className="capitalize">{c.name}</span>
                    <span className="text-[var(--muted-foreground)]">{Math.round(c.score * 100)}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-[var(--muted)]">
                    <div className="h-full bg-[var(--primary)]" style={{ width: `${Math.round(c.score * 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
            <ul className="list-inside list-disc text-xs text-[var(--muted-foreground)]">
              {score.data?.drivers.map((driver) => <li key={driver}>{driver}</li>)}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> Early warnings
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {alerts.data?.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">All clear - no alerts.</p>}
            {alerts.data?.map((alert, index) => (
              <div key={index} className={cn("rounded-md border border-l-4 px-3 py-2 text-xs", severityBg(alert.severity))}>
                <div className="font-medium">
                  {alert.severity.toUpperCase()} - {alert.title}
                </div>
                <div className="mt-0.5 text-[var(--muted-foreground)]">{alert.detail}</div>
                <div className="mt-0.5">{alert.recommendation}</div>
              </div>
            ))}
            {alerts.isLoading && <p className="text-sm text-[var(--muted-foreground)]">Loading...</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" /> Academic outlook
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            <div className="flex justify-between">
              <span className="text-[var(--muted-foreground)]">Current GPA</span>
              <span className="font-semibold">{profile.data?.gpa ?? "..."}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--muted-foreground)]">Projected GPA</span>
              <span className="font-semibold">{predictions.data?.projected_gpa ?? "..."}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--muted-foreground)]">Overall attendance</span>
              <span className="font-semibold">
                {profile.data ? `${Math.round(profile.data.overall_attendance * 100)}%` : "..."}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--muted-foreground)]">Credits earned</span>
              <span className="font-semibold">{profile.data?.credits_earned ?? "..."}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--muted-foreground)]">Course load</span>
              <span className="font-semibold">{profile.data?.course_load ?? "..."}</span>
            </div>
            <div className="mt-2 rounded-md border border-[var(--border)] bg-[var(--muted)] px-3 py-2 text-xs text-[var(--muted-foreground)]">
              {predictions.data?.note}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-4 w-4" /> My courses
          </CardTitle>
        </CardHeader>
        <CardContent>
          {profile.data?.courses.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">No enrollments found.</p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                  <th className="py-2 pr-4">Course</th>
                  <th className="py-2 pr-4">Credits</th>
                  <th className="py-2 pr-4">Grade</th>
                  <th className="py-2 pr-4">Marks</th>
                  <th className="py-2 pr-4">Attendance</th>
                  <th className="py-2 pr-4">Predicted pass</th>
                </tr>
              </thead>
              <tbody>
                {profile.data?.courses.map((course) => {
                  const prediction = predictions.data?.predictions.find(
                    (p) => p.course_code === course.course_code
                  );
                  return (
                    <tr key={course.course_code} className="border-b border-[var(--border)]">
                      <td className="py-2 pr-4 font-medium">
                        {course.course_code} <span className="text-xs font-normal text-[var(--muted-foreground)]">{course.title}</span>
                      </td>
                      <td className="py-2 pr-4">{course.credits}</td>
                      <td className="py-2 pr-4">
                        {course.status === "ongoing" ? (
                          <span className="text-[var(--muted-foreground)]">ongoing</span>
                        ) : (
                          <span className={cn("font-medium", course.grade === "F" && "text-red-600")}>{course.grade}</span>
                        )}
                      </td>
                      <td className="py-2 pr-4">{course.marks ?? "-"}</td>
                      <td className="py-2 pr-4">
                        <span className={cn(course.attendance_rate < 0.75 && "font-medium text-red-600")}>
                          {Math.round(course.attendance_rate * 100)}%
                        </span>
                      </td>
                      <td className="py-2 pr-4">
                        {prediction ? (
                          <span className={cn("font-medium", riskColor(prediction.risk_level))}>
                            {Math.round(prediction.pass_probability * 100)}%
                          </span>
                        ) : (
                          "-"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarCheck className="h-4 w-4" /> Personal AI Advisor
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" variant="outline" onClick={runToday} disabled={advisorBusy}>
              {advisorBusy ? "Working..." : "What should I do today?"}
            </Button>
            <form onSubmit={runAdvise} className="flex gap-2">
              <Input
                value={courseCode}
                onChange={(e) => setCourseCode(e.target.value)}
                placeholder="Check eligibility, e.g. CS3491"
                className="h-8 w-64 text-sm"
                disabled={advisorBusy}
              />
              <Button size="sm" type="submit" disabled={advisorBusy || !courseCode.trim()}>
                Check
              </Button>
            </form>
          </div>

          {today && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-[var(--muted-foreground)]">Today's plan for {today.date}</span>
                <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", riskColor(today.risk_level))}>
                  {today.risk_level.toUpperCase()} RISK
                </span>
              </div>
              {plan.map((item, index) => (
                <div key={index} className={cn("rounded-md border border-l-4 px-3 py-2 text-xs", severityBg(item.severity))}>
                  <div className="font-medium">
                    {item.severity.toUpperCase()} {item.kind === "study" ? "- study focus" : ""}
                  </div>
                  <div>{item.action}</div>
                </div>
              ))}
            </div>
          )}

          {advice && (
            <div
              className={cn(
                "rounded-md border border-l-4 px-3 py-2 text-sm",
                advice.eligible ? "border-l-green-500 bg-green-50" : "border-l-amber-500 bg-amber-50"
              )}
            >
              <div className="font-medium">
                {advice.eligible ? "Eligible" : "Not eligible"} - {advice.course_code} {advice.course_title}
              </div>
              <div className="mt-0.5">{advice.reason}</div>
              {advice.unmet_prerequisites.length > 0 && (
                <div className="mt-0.5 text-xs text-[var(--muted-foreground)]">
                  Missing prerequisites: {advice.unmet_prerequisites.join(", ")}
                </div>
              )}
              {advice.chain.length > 0 && (
                <div className="mt-0.5 text-xs text-[var(--muted-foreground)]">
                  Prerequisite chain: {advice.chain.join(" -> ")}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GraduationCap className="h-4 w-4" /> Your grounded AI assistant
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--muted-foreground)]">
            For anything else - syllabus questions, curriculum lookups, attendance rules, or registration
            policies - ask the AI Assistant in the Chat page. Answers are grounded in the university knowledge
            base with page citations.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
