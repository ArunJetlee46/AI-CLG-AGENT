import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  ClipboardList,
  Compass,
  FileText,
  GraduationCap,
  LineChart,
  Rocket,
  Sparkles,
  TrendingUp,
  Trophy,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Skeleton } from "@/core/components/ui/skeleton";
import { studentApi } from "@/modules/student/api";
import { cn } from "@/core/lib/utils";
import { useAuthStore } from "@/core/stores/auth";

const TOOLS = [
  {
    to: "/student/insights",
    label: "My Insights",
    blurb: "Digital twin, career readiness, weaknesses and progress charts.",
    icon: TrendingUp,
    accent: "text-violet-600 bg-violet-100",
  },
  {
    to: "/student/community",
    label: "Community",
    blurb: "Study partners, course recommendations, badges and rewards.",
    icon: Trophy,
    accent: "text-amber-600 bg-amber-100",
  },
  {
    to: "/student/exam-prep",
    label: "Exam Prep",
    blurb: "AI-generated practice quizzes with answers and explanations.",
    icon: BookOpen,
    accent: "text-teal-600 bg-teal-100",
  },
  {
    to: "/student/assignment-assistant",
    label: "Assignment Assistant",
    blurb: "Step-by-step plans, hints and marking rubrics for your work.",
    icon: ClipboardList,
    accent: "text-indigo-600 bg-indigo-100",
  },
  {
    to: "/student/mock-interview",
    label: "Mock Interview",
    blurb: "Role-specific questions with scored, actionable feedback.",
    icon: Users,
    accent: "text-fuchsia-600 bg-fuchsia-100",
  },
  {
    to: "/student/resume-ats",
    label: "Resume ATS",
    blurb: "Check your resume against ATS parsing rules and improve it.",
    icon: FileText,
    accent: "text-rose-600 bg-rose-100",
  },
  {
    to: "/student/project-mentor",
    label: "Project Mentor",
    blurb: "Milestone plans and blocker help for your projects.",
    icon: Rocket,
    accent: "text-orange-600 bg-orange-100",
  },
  {
    to: "/chat?q=How%20do%20I%20register%20for%20a%20course%3F",
    label: "AI Curriculum Tutor",
    blurb: "Ask anything — answers grounded in the knowledge base with citations.",
    icon: Compass,
    accent: "text-sky-600 bg-sky-100",
  },
] as const;

const riskTone = (level: string) =>
  level === "high" ? "destructive" : level === "medium" ? "warning" : "success";

export function StudentLanding() {
  const token = useAuthStore((s) => s.token);
  const username = useAuthStore((s) => s.username);

  const profile = useQuery({ queryKey: ["me"], queryFn: () => studentApi.profile(token!), enabled: !!token, refetchInterval: 60_000 });
  const score = useQuery({ queryKey: ["me-score"], queryFn: () => studentApi.successScore(token!), enabled: !!token, refetchInterval: 60_000 });
  const career = useQuery({ queryKey: ["me-career"], queryFn: () => studentApi.careerReadiness(token!), enabled: !!token, refetchInterval: 60_000 });
  const today = useQuery({ queryKey: ["me-today"], queryFn: () => studentApi.today(token!), enabled: !!token, refetchInterval: 60_000 });

  const stats = [
    { label: "Success score", value: score.data?.success_score, sub: `${score.data?.risk_level ?? "—"} risk`, accent: "from-emerald-500 to-teal-500" },
    { label: "GPA", value: profile.data?.gpa, sub: "out of 4", accent: "from-violet-500 to-fuchsia-500" },
    { label: "Attendance", value: profile.data ? `${Math.round(profile.data.overall_attendance * 100)}%` : undefined, sub: `${profile.data?.course_load ?? "—"} courses`, accent: "from-sky-500 to-cyan-500" },
    { label: "Career readiness", value: career.data?.career_readiness_score, sub: career.data?.band ?? "—", accent: "from-amber-500 to-orange-500" },
  ];

  const statsLoading = profile.isLoading || score.isLoading || career.isLoading;

  return (
    <div className="relative flex flex-col gap-8 overflow-hidden">
      <div className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-sky-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -left-32 top-40 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />

      <section className="fade-up relative rounded-3xl border border-[var(--border)] bg-gradient-to-br from-[var(--primary)]/10 via-white/80 to-white p-8 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <Badge tone="primary">STUDENT COPILOT</Badge>
            <h1 className="mt-3 text-3xl font-extrabold tracking-tight lg:text-4xl">
              Welcome back, {username}
            </h1>
            <p className="mt-2 max-w-xl text-sm text-[var(--muted-foreground)]">
              {profile.data
                ? `${profile.data.student_id} · ${profile.data.program} · Year ${profile.data.year}`
                : "Your personal academic copilot"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/student/dashboard">
              <Button size="lg">
                Open my dashboard <ArrowRight className="ml-1.5 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {statsLoading && !profile.data && !score.data && !career.data ? (
            <>
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex flex-col gap-2 rounded-2xl border border-[var(--border)] bg-white/80 p-4 backdrop-blur">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-8 w-14" />
                  <Skeleton className="h-3 w-16" />
                </div>
              ))}
            </>
          ) : (
            stats.map(({ label, value, sub, accent }) => (
              <div key={label} className="rounded-2xl border border-[var(--border)] bg-white/80 p-4 backdrop-blur">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-[var(--muted-foreground)]">{label}</p>
                  <span className={`h-1.5 w-1.5 rounded-full bg-gradient-to-r ${accent}`} />
                </div>
                <p className="mt-1 text-3xl font-extrabold">{value ?? "—"}</p>
                <p className="text-xs capitalize text-[var(--muted-foreground)]">{sub}</p>
              </div>
            ))
          )}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="fade-up lg:col-span-2">
          <div className="mb-3 flex items-center gap-2">
            <LineChart className="h-4 w-4 text-[var(--primary)]" />
            <h2 className="text-lg font-bold tracking-tight">Everything you need to succeed</h2>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {TOOLS.map(({ to, label, blurb, icon: Icon, accent }) => (
              <Link
                key={to}
                to={to}
                className="card-shell group flex items-start gap-3 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 transition-all hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/5"
              >
                <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${accent}`}>
                  <Icon className="h-5 w-5" />
                </span>
                <span className="min-w-0">
                  <span className="flex items-center gap-1.5 text-sm font-semibold">
                    {label}
                    <ArrowRight className="h-3.5 w-3.5 text-[var(--muted-foreground)] opacity-0 transition-opacity group-hover:opacity-100" />
                  </span>
                  <span className="mt-0.5 block text-xs leading-relaxed text-[var(--muted-foreground)]">{blurb}</span>
                </span>
              </Link>
            ))}
          </div>
        </section>

        <section className="fade-up">
          <div className="card-shell flex flex-col gap-3 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[var(--primary)]" />
              <h2 className="text-sm font-bold">Today's focus</h2>
              {today.data && (
                <Badge tone={riskTone(today.data.risk_level)} className="ml-auto">
                  {today.data.risk_level.toUpperCase()} RISK
                </Badge>
              )}
            </div>
            <p className="text-xs text-[var(--muted-foreground)]">
              Your personalized plan for {today.data?.date ?? "today"} — generated from live attendance, grades and risk.
            </p>
            <div className="flex flex-col gap-2">
              {today.data?.plan.slice(0, 4).map((item, i) => (
                <div
                  key={i}
                  className={cn(
                    "rounded-lg border border-l-4 px-3 py-2 text-xs",
                    item.severity === "high"
                      ? "border-l-red-500 bg-red-50"
                      : item.severity === "medium"
                        ? "border-l-amber-500 bg-amber-50"
                        : "border-l-green-500 bg-green-50"
                  )}
                >
                  <span className="font-semibold capitalize">{item.severity}</span>
                  {item.kind === "study" && <span className="text-[var(--muted-foreground)]"> · study focus</span>}
                  <p className="mt-0.5 text-[var(--muted-foreground)]">{item.action}</p>
                </div>
              ))}
              {today.isLoading && <p className="text-xs text-[var(--muted-foreground)]">Building your plan…</p>}
              {!today.isLoading && !today.data?.plan.length && (
                <p className="text-xs text-[var(--muted-foreground)]">All clear — no alerts today.</p>
              )}
            </div>
            <Link to="/student/dashboard" className="mt-1 text-xs font-medium text-[var(--primary)] hover:underline">
              View full dashboard →
            </Link>
          </div>

          <div className="card-shell mt-4 rounded-2xl border border-[var(--border)] bg-gradient-to-br from-[var(--primary)]/10 to-transparent p-5">
            <h3 className="text-sm font-bold">Need a quick answer?</h3>
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">
              The Curriculum Tutor answers syllabus, policy and registration questions — grounded in the knowledge
              base with page citations.
            </p>
            <Link to="/chat" className="mt-3 inline-block">
              <Button size="sm" variant="outline">
                <GraduationCap className="mr-1.5 h-4 w-4" /> Open AI tutor
              </Button>
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
