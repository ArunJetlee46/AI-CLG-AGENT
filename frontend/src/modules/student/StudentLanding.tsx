import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import {
  ArrowRight,
  Award,
  BookOpen,
  Bell,
  CalendarClock,
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

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function ProgressRing({
  value,
  max = 100,
  size = 56,
  stroke = 5,
  color = "var(--primary)",
}: {
  value: number;
  max?: number;
  size?: number;
  stroke?: number;
  color?: string;
}) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(Math.max(value / max, 0), 1);
  const offset = circ * (1 - pct);

  return (
    <svg width={size} height={size} className="shrink-0 -rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        className="transition-[stroke-dashoffset] duration-1000 ease-out"
      />
    </svg>
  );
}

const QUICK_ACTIONS = [
  { to: "/student/exam-prep", label: "Exam Prep", icon: BookOpen, accent: "text-teal-600 bg-teal-100" },
  { to: "/student/mock-interview", label: "Mock Interview", icon: Users, accent: "text-fuchsia-600 bg-fuchsia-100" },
  { to: "/chat?q=How%20do%20I%20register%20for%20a%20course%3F", label: "AI Tutor", icon: Compass, accent: "text-sky-600 bg-sky-100" },
  { to: "/student/schedule", label: "Schedule", icon: CalendarClock, accent: "text-indigo-600 bg-indigo-100" },
] as const;

const TOOLS = [
  { to: "/student/insights", label: "My Insights", blurb: "Digital twin, career readiness, weaknesses and progress charts.", icon: TrendingUp, accent: "text-violet-600 bg-violet-100" },
  { to: "/student/community", label: "Community", blurb: "Study partners, course recommendations, badges and rewards.", icon: Trophy, accent: "text-amber-600 bg-amber-100" },
  { to: "/student/assignment-assistant", label: "Assignment Assistant", blurb: "Step-by-step plans, hints and marking rubrics for your work.", icon: ClipboardList, accent: "text-indigo-600 bg-indigo-100" },
  { to: "/student/resume-ats", label: "Resume ATS", blurb: "Check your resume against ATS parsing rules and improve it.", icon: FileText, accent: "text-rose-600 bg-rose-100" },
  { to: "/student/project-mentor", label: "Project Mentor", blurb: "Milestone plans and blocker help for your projects.", icon: Rocket, accent: "text-orange-600 bg-orange-100" },
  { to: "/student/placements", label: "Placements", blurb: "Apply to drives, track applications and accept offers.", icon: GraduationCap, accent: "text-emerald-600 bg-emerald-100" },
  { to: "/student/degree-audit", label: "Degree Audit", blurb: "Track degree progress, credits earned and requirements.", icon: LineChart, accent: "text-cyan-600 bg-cyan-100" },
  { to: "/student/study-assist", label: "Study Assist", blurb: "AI-powered curriculum tutor grounded in your syllabus.", icon: BookOpen, accent: "text-sky-600 bg-sky-100" },
] as const;

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const riskTone = (level: string) =>
  level === "high" ? "destructive" : level === "medium" ? "warning" : "success";

const severityBorder = (s: string) =>
  s === "high" ? "border-l-red-500 bg-red-50" : s === "medium" ? "border-l-amber-500 bg-amber-50" : "border-l-green-500 bg-green-50";

const notifAccent = (type: string) => {
  switch (type) {
    case "risk": return "text-red-600 bg-red-100";
    case "shortlist": return "text-emerald-600 bg-emerald-100";
    case "milestone": return "text-amber-600 bg-amber-100";
    case "drive": return "text-sky-600 bg-sky-100";
    default: return "text-[var(--muted-foreground)] bg-[var(--muted)]";
  }
};

export function StudentLanding() {
  const token = useAuthStore((s) => s.token);
  const username = useAuthStore((s) => s.username);

  const profile = useQuery({ queryKey: ["me"], queryFn: () => studentApi.profile(token!), enabled: !!token, refetchInterval: 60_000 });
  const score = useQuery({ queryKey: ["me-score"], queryFn: () => studentApi.successScore(token!), enabled: !!token, refetchInterval: 60_000 });
  const career = useQuery({ queryKey: ["me-career"], queryFn: () => studentApi.careerReadiness(token!), enabled: !!token, refetchInterval: 60_000 });
  const today = useQuery({ queryKey: ["me-today"], queryFn: () => studentApi.today(token!), enabled: !!token, refetchInterval: 60_000 });
  const timetable = useQuery({ queryKey: ["me-timetable"], queryFn: () => studentApi.myTimetable(token!), enabled: !!token });
  const notifications = useQuery({ queryKey: ["me-notes"], queryFn: () => studentApi.notifications(token!), enabled: !!token });
  const gamification = useQuery({ queryKey: ["me-gam"], queryFn: () => studentApi.gamification(token!), enabled: !!token });

  const loading = profile.isLoading || score.isLoading || career.isLoading;

  const upcoming = useMemo(() => {
    if (!timetable.data) return [];
    const now = new Date();
    const dayIdx = (now.getDay() + 6) % 7;
    const mins = now.getHours() * 60 + now.getMinutes();
    const result: { day: string; entry: (typeof timetable.data.entries)[0] }[] = [];
    for (let offset = 0; offset < 7 && result.length < 3; offset++) {
      const di = (dayIdx + offset) % 7;
      const dayName = DAYS[di];
      for (const entry of timetable.data.by_day[dayName] ?? []) {
        const [sh, sm] = entry.start_time.split(":").map(Number);
        if (offset > 0 || sh * 60 + sm > mins) {
          result.push({ day: dayName, entry });
          if (result.length >= 3) break;
        }
      }
    }
    return result;
  }, [timetable.data]);

  const earnedBadges = gamification.data?.badges.filter((b) => b.earned).slice(0, 3) ?? [];

  return (
    <div className="relative flex flex-col gap-8 overflow-hidden">
      <div className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-sky-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -left-32 top-40 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />

      {/* Hero */}
      <section
        className="fade-up relative overflow-hidden rounded-3xl border border-[var(--border)] bg-gradient-to-br from-[var(--primary)]/10 via-white/80 to-white p-8 backdrop-blur"
        style={{ "--d": "0ms" } as React.CSSProperties}
      >
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-[var(--primary)]/5 blur-2xl" />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <Badge tone="primary">STUDENT COPILOT</Badge>
            <h1 className="mt-3 text-3xl font-extrabold tracking-tight lg:text-4xl">
              {greeting()}, {username}
            </h1>
            <p className="mt-2 max-w-xl text-sm text-[var(--muted-foreground)]">
              {profile.data
                ? `${profile.data.student_id} · ${profile.data.program} · Year ${profile.data.year}`
                : "Your personal academic copilot — powered by AI"}
            </p>
          </div>
          <Link to="/student/dashboard">
            <Button size="lg">
              Open dashboard <ArrowRight className="ml-1.5 h-4 w-4" />
            </Button>
          </Link>
        </div>

        {/* Quick Actions */}
        <div className="mt-6 flex flex-wrap gap-2">
          {QUICK_ACTIONS.map(({ to, label, icon: Icon, accent }) => (
            <Link
              key={to}
              to={to}
              className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-white/80 px-4 py-2 text-sm font-medium backdrop-blur transition-all hover:-translate-y-0.5 hover:shadow-md hover:shadow-black/5"
            >
              <span className={`grid h-6 w-6 place-items-center rounded-full ${accent}`}>
                <Icon className="h-3.5 w-3.5" />
              </span>
              {label}
            </Link>
          ))}
        </div>
      </section>

      {/* Stats Rings */}
      <section
        className="fade-up grid grid-cols-2 gap-3 lg:grid-cols-4"
        style={{ "--d": "60ms" } as React.CSSProperties}
      >
        {loading && !profile.data ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4">
              <Skeleton className="h-14 w-14 shrink-0 rounded-full" />
              <div className="flex flex-col gap-2">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-6 w-14" />
                <Skeleton className="h-3 w-16" />
              </div>
            </div>
          ))
        ) : (
          <>
            <div className="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 transition-all hover:-translate-y-0.5 hover:shadow-md">
              <ProgressRing value={score.data?.success_score ?? 0} color="#10b981" />
              <div className="min-w-0">
                <p className="text-xs text-[var(--muted-foreground)]">Success Score</p>
                <p className="text-2xl font-extrabold">{score.data?.success_score ?? "\u2014"}</p>
                <p className="text-xs capitalize text-[var(--muted-foreground)]">{score.data?.risk_level ?? "\u2014"} risk</p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 transition-all hover:-translate-y-0.5 hover:shadow-md">
              <ProgressRing value={profile.data?.gpa ?? 0} max={4} color="#8b5cf6" />
              <div className="min-w-0">
                <p className="text-xs text-[var(--muted-foreground)]">GPA</p>
                <p className="text-2xl font-extrabold">{profile.data?.gpa ?? "\u2014"}</p>
                <p className="text-xs text-[var(--muted-foreground)]">out of 4.0</p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 transition-all hover:-translate-y-0.5 hover:shadow-md">
              <ProgressRing value={profile.data ? profile.data.overall_attendance * 100 : 0} color="#0ea5e9" />
              <div className="min-w-0">
                <p className="text-xs text-[var(--muted-foreground)]">Attendance</p>
                <p className="text-2xl font-extrabold">{profile.data ? `${Math.round(profile.data.overall_attendance * 100)}%` : "\u2014"}</p>
                <p className="text-xs text-[var(--muted-foreground)]">{profile.data?.course_load ?? "\u2014"} courses</p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 transition-all hover:-translate-y-0.5 hover:shadow-md">
              <ProgressRing value={career.data?.career_readiness_score ?? 0} color="#f59e0b" />
              <div className="min-w-0">
                <p className="text-xs text-[var(--muted-foreground)]">Career Readiness</p>
                <p className="text-2xl font-extrabold">{career.data?.career_readiness_score ?? "\u2014"}</p>
                <p className="text-xs capitalize text-[var(--muted-foreground)]">{career.data?.band ?? "\u2014"}</p>
              </div>
            </div>
          </>
        )}
      </section>

      {/* Two-Column Body */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        {/* Left Column */}
        <div className="flex flex-col gap-6 lg:col-span-2">

          {/* Today's Focus */}
          <section
            className="fade-up rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5"
            style={{ "--d": "120ms" } as React.CSSProperties}
          >
            <div className="mb-3 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[var(--primary)]" />
              <h2 className="text-sm font-bold">Today's focus</h2>
              {today.data && (
                <Badge tone={riskTone(today.data.risk_level)} className="ml-auto">
                  {today.data.risk_level.toUpperCase()} RISK
                </Badge>
              )}
            </div>
            <p className="mb-3 text-xs text-[var(--muted-foreground)]">
              Personalized plan for {today.data?.date ?? "today"} — generated from live attendance, grades and risk.
            </p>
            <div className="flex flex-col gap-2">
              {(today.data?.plan ?? []).slice(0, 5).map((item, i) => (
                <div key={i} className={cn("rounded-lg border border-l-4 px-3 py-2 text-xs", severityBorder(item.severity))}>
                  <span className="font-semibold capitalize">{item.severity}</span>
                  {item.course_code && <span className="ml-1 text-[var(--muted-foreground)]">\u00b7 {item.course_code}</span>}
                  <p className="mt-0.5 text-[var(--muted-foreground)]">{item.action}</p>
                </div>
              ))}
              {today.isLoading && <p className="text-xs text-[var(--muted-foreground)]">Building your plan...</p>}
              {!today.isLoading && !(today.data?.plan.length) && (
                <p className="text-xs text-[var(--muted-foreground)]">All clear — no alerts today.</p>
              )}
            </div>
            <Link to="/student/dashboard" className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-[var(--primary)] hover:underline">
              View full dashboard <ArrowRight className="h-3 w-3" />
            </Link>
          </section>

          {/* Tools Grid */}
          <section
            className="fade-up"
            style={{ "--d": "180ms" } as React.CSSProperties}
          >
            <div className="mb-3 flex items-center gap-2">
              <LineChart className="h-4 w-4 text-[var(--primary)]" />
              <h2 className="text-sm font-bold">Everything you need to succeed</h2>
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
        </div>

        {/* Right Column */}
        <div className="flex flex-col gap-6">

          {/* Upcoming Schedule */}
          <section
            className="fade-up rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5"
            style={{ "--d": "140ms" } as React.CSSProperties}
          >
            <div className="mb-3 flex items-center gap-2">
              <CalendarClock className="h-4 w-4 text-[var(--primary)]" />
              <h2 className="text-sm font-bold">Upcoming classes</h2>
            </div>
            {timetable.isLoading && (
              <div className="flex flex-col gap-2">
                {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
              </div>
            )}
            {!timetable.isLoading && upcoming.length === 0 && (
              <p className="text-xs text-[var(--muted-foreground)]">No upcoming classes this week.</p>
            )}
            <div className="flex flex-col gap-2">
              {upcoming.map(({ day, entry }, i) => (
                <div key={i} className="flex items-start gap-3 rounded-lg border border-[var(--border)] bg-[var(--muted)]/30 px-3 py-2">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--primary)]/10 text-[var(--primary)]">
                    <span className="text-[10px] font-bold leading-none">{entry.start_time.slice(0, 5)}</span>
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold">{entry.course_code}</p>
                    <p className="truncate text-[11px] text-[var(--muted-foreground)]">{entry.course_title}</p>
                    <p className="text-[10px] text-[var(--muted-foreground)]">{day} \u00b7 {entry.room} \u00b7 {entry.lecturer}</p>
                  </div>
                </div>
              ))}
            </div>
            <Link to="/student/schedule" className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-[var(--primary)] hover:underline">
              View full schedule <ArrowRight className="h-3 w-3" />
            </Link>
          </section>

          {/* Recent Notifications */}
          <section
            className="fade-up rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5"
            style={{ "--d": "200ms" } as React.CSSProperties}
          >
            <div className="mb-3 flex items-center gap-2">
              <Bell className="h-4 w-4 text-[var(--primary)]" />
              <h2 className="text-sm font-bold">Recent notifications</h2>
            </div>
            {notifications.isLoading && (
              <div className="flex flex-col gap-2">
                {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
              </div>
            )}
            {!notifications.isLoading && !notifications.data?.notifications.length && (
              <p className="text-xs text-[var(--muted-foreground)]">No notifications yet.</p>
            )}
            <div className="flex flex-col gap-2">
              {(notifications.data?.notifications ?? []).slice(0, 4).map((n, i) => (
                <div key={i} className="flex items-start gap-2.5 rounded-lg border border-[var(--border)] px-3 py-2">
                  <span className={cn("mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg text-[10px] font-bold", notifAccent(n.type))}>
                    {n.type.charAt(0).toUpperCase()}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold">{n.title}</p>
                    <p className="truncate text-[11px] text-[var(--muted-foreground)]">{n.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Gamification */}
          <section
            className="fade-up rounded-2xl border border-[var(--border)] bg-gradient-to-br from-[var(--primary)]/5 to-transparent p-5"
            style={{ "--d": "240ms" } as React.CSSProperties}
          >
            <div className="mb-3 flex items-center gap-2">
              <Trophy className="h-4 w-4 text-amber-500" />
              <h2 className="text-sm font-bold">Your progress</h2>
            </div>
            {gamification.isLoading && <Skeleton className="h-20 w-full rounded-lg" />}
            {gamification.data && (
              <>
                <div className="mb-3 flex items-center gap-3">
                  <div className="grid h-12 w-12 place-items-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500 text-sm font-bold text-white shadow-md">
                    Lv.{gamification.data.level}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold">{gamification.data.xp} / {gamification.data.xp_to_next_level} XP</p>
                    <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-[var(--muted)]">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500 transition-all duration-700"
                        style={{ width: `${Math.round(gamification.data.level_progress * 100)}%` }}
                      />
                    </div>
                    <p className="mt-1 text-[10px] text-[var(--muted-foreground)]">{gamification.data.xp_in_level} XP to next level</p>
                  </div>
                </div>
                {earnedBadges.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {earnedBadges.map((b) => (
                      <span key={b.id} className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[10px] font-medium text-amber-700">
                        <Award className="h-3 w-3" /> {b.name}
                      </span>
                    ))}
                  </div>
                )}
              </>
            )}
            {!gamification.isLoading && !gamification.data && (
              <p className="text-xs text-[var(--muted-foreground)]">Complete tasks to earn XP and badges.</p>
            )}
            <Link to="/student/community" className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-[var(--primary)] hover:underline">
              View community <ArrowRight className="h-3 w-3" />
            </Link>
          </section>

          {/* AI Tutor CTA */}
          <section
            className="fade-up rounded-2xl border border-[var(--border)] bg-gradient-to-br from-[var(--primary)]/10 to-transparent p-5"
            style={{ "--d": "280ms" } as React.CSSProperties}
          >
            <h3 className="text-sm font-bold">Need a quick answer?</h3>
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">
              The Curriculum Tutor answers syllabus, policy and registration questions — grounded in the knowledge base with citations.
            </p>
            <Link to="/chat" className="mt-3 inline-block">
              <Button size="sm" variant="outline">
                <GraduationCap className="mr-1.5 h-4 w-4" /> Open AI tutor
              </Button>
            </Link>
          </section>
        </div>
      </div>
    </div>
  );
}
