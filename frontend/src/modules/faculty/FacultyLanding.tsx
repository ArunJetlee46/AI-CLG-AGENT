import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Bot,
  CalendarClock,
  CopyX,
  FileBarChart,
  GraduationCap,
  Handshake,
  LayoutDashboard,
  LifeBuoy,
  MessagesSquare,
  ScrollText,
  Sparkles,
  TrendingDown,
  Wrench,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { facultyApi } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";

const TOOLS = [
  { to: "/faculty/dashboard", label: "My Dashboard", blurb: "Course health, attendance, at-risk flags and interventions.", icon: LayoutDashboard, accent: "text-sky-600 bg-sky-100" },
  { to: "/faculty/intelligence", label: "Faculty Intelligence", blurb: "AI recommendations, learning outcomes and high performers.", icon: Sparkles, accent: "text-amber-600 bg-amber-100" },
  { to: "/faculty/copilot", label: "Faculty Copilot", blurb: "Analysis → recommendation → approval → execute → audit pipeline.", icon: Bot, accent: "text-violet-600 bg-violet-100" },
  { to: "/faculty/course-reports", label: "Course Reports", blurb: "Health score, grade distribution and narrative per course.", icon: FileBarChart, accent: "text-emerald-600 bg-emerald-100" },
  { to: "/faculty/similarity", label: "Similarity Check", blurb: "Screening for similar submissions across students.", icon: CopyX, accent: "text-rose-600 bg-rose-100" },
  { to: "/faculty/remedial", label: "Remedial Plans", blurb: "Personalized rescue plans for at-risk students.", icon: LifeBuoy, accent: "text-teal-600 bg-teal-100" },
  { to: "/faculty/tools", label: "Faculty Tools", blurb: "Question papers, lesson plans, evaluation, code review, lab.", icon: Wrench, accent: "text-indigo-600 bg-indigo-100" },
  { to: "/faculty/schedule", label: "My Schedule", blurb: "Weekly teaching timetable across your assigned courses.", icon: CalendarClock, accent: "text-indigo-600 bg-indigo-100" },
  { to: "/faculty/placements", label: "Placement Overview", blurb: "Placement readiness of students in your courses.", icon: Handshake, accent: "text-emerald-600 bg-emerald-100" },
  { to: "/faculty/study-assist", label: "Study Assistant", blurb: "Curriculum-grounded Q&A for your courses.", icon: MessagesSquare, accent: "text-teal-600 bg-teal-100" },
  { to: "/faculty/audit", label: "Audit Log", blurb: "Approved interventions and every tracked action.", icon: ScrollText, accent: "text-slate-600 bg-slate-100" },
] as const;

export function FacultyLanding() {
  const token = useAuthStore((s) => s.token);
  const username = useAuthStore((s) => s.username);

  const me = useQuery({ queryKey: ["fac-me"], queryFn: () => facultyApi.me(token!), enabled: !!token });
  const overview = useQuery({ queryKey: ["fac-overview"], queryFn: () => facultyApi.overview(token!), enabled: !!token });

  const stats = [
    { label: "Courses", value: overview.data?.courses.length ?? me.data?.course_count ?? "…", sub: "assigned to you", accent: "from-violet-500 to-purple-500" },
    { label: "Students", value: overview.data?.summary.students ?? "…", sub: "across your courses", accent: "from-sky-500 to-cyan-500" },
    { label: "At-risk", value: overview.data?.summary.at_risk ?? "…", sub: "flagged for attention", accent: "from-rose-500 to-red-500" },
    { label: "Avg GPA", value: overview.data?.summary.average?.toFixed(2) ?? "…", sub: `${overview.data?.summary.pass_rate ?? "…"}% pass rate`, accent: "from-emerald-500 to-teal-500" },
  ];

  const trends = overview.data?.trends ?? [];

  return (
    <div className="relative flex flex-col gap-8 overflow-hidden">
      <div className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-violet-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -left-32 top-40 h-72 w-72 rounded-full bg-sky-500/10 blur-3xl" />

      <section className="fade-up relative rounded-3xl border border-[var(--border)] bg-gradient-to-br from-violet-500/10 via-white/80 to-white p-8 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <Badge tone="primary">FACULTY COPILOT</Badge>
            <h1 className="mt-3 text-3xl font-extrabold tracking-tight lg:text-4xl">
              Welcome back, {username}
            </h1>
            <p className="mt-2 max-w-xl text-sm text-[var(--muted-foreground)]">
              Course health, at-risk signals and LLM tools — from analysis to approved intervention.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/faculty/copilot">
              <Button size="lg">
                Open pipeline <ArrowRight className="ml-1.5 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {stats.map(({ label, value, sub, accent }) => (
            <div key={label} className="rounded-2xl border border-[var(--border)] bg-white/80 p-4 backdrop-blur">
              <div className="flex items-center justify-between">
                <p className="text-xs text-[var(--muted-foreground)]">{label}</p>
                <span className={`h-1.5 w-1.5 rounded-full bg-gradient-to-r ${accent}`} />
              </div>
              <p className="mt-1 text-3xl font-extrabold">{value}</p>
              <p className="text-xs text-[var(--muted-foreground)]">{sub}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="fade-up lg:col-span-2">
          <div className="mb-3 flex items-center gap-2">
            <GraduationCap className="h-4 w-4 text-[var(--primary)]" />
            <h2 className="text-lg font-bold tracking-tight">Everything a faculty member needs</h2>
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
              <TrendingDown className="h-4 w-4 text-[var(--primary)]" />
              <h2 className="text-sm font-bold">Course health trends</h2>
            </div>
            <div className="flex flex-col gap-1.5">
              {trends.slice(0, 6).map((t) => (
                <div key={t.course_code} className="flex items-center gap-2 text-xs">
                  <Badge tone="neutral" className="shrink-0 font-mono">{t.course_code}</Badge>
                  <span className="min-w-0 flex-1 truncate text-[var(--muted-foreground)]">{t.detail}</span>
                </div>
              ))}
              {trends.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">Loading health trends…</p>}
            </div>
            <Link to="/faculty/dashboard" className="mt-1 text-xs font-medium text-[var(--primary)] hover:underline">
              Open my dashboard →
            </Link>
          </div>

          <div className="card-shell mt-4 rounded-2xl border border-[var(--border)] bg-gradient-to-br from-violet-500/10 to-transparent p-5">
            <h3 className="flex items-center gap-1.5 text-sm font-bold">
              <Sparkles className="h-4 w-4 text-[var(--primary)]" /> Quick actions
            </h3>
            <div className="mt-3 flex flex-col gap-2">
              <Link to="/faculty/tools/question-paper" className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-medium transition-colors hover:bg-[var(--muted)]">
                Generate a question paper →
              </Link>
              <Link to="/faculty/remedial" className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-medium transition-colors hover:bg-[var(--muted)]">
                Build a remedial plan →
              </Link>
              <Link to="/faculty/similarity" className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-medium transition-colors hover:bg-[var(--muted)]">
                Run a similarity check →
              </Link>
              <Link to="/faculty/audit" className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-medium transition-colors hover:bg-[var(--muted)]">
                Review the audit trail →
              </Link>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
