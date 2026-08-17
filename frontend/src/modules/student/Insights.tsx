import { useQuery } from "@tanstack/react-query";
import {
  Award,
  BookOpen,
  ChevronRight,
  Lightbulb,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  TrendingDown,
  TriangleAlert,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "@/core/components/ui/badge";
import { Skeleton } from "@/core/components/ui/skeleton";
import { studentApi } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";
import { cn } from "@/core/lib/utils";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function ProgressRing({
  value,
  max = 100,
  size = 64,
  stroke = 6,
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

const trendTone = (trend: string) =>
  trend === "improving" ? "success" : trend === "declining" ? "destructive" : "neutral";

const riskBorder = (level: string) =>
  level === "high" ? "border-l-red-500 bg-red-50/50" : level === "medium" ? "border-l-amber-500 bg-amber-50/50" : "border-l-green-500 bg-green-50/50";

const chart = (points: { week: number; value: number }[], scale: (v: number) => number) =>
  points.map((p) => ({ week: `W${p.week}`, value: scale(p.value) }));

export function Insights() {
  const token = useAuthStore((s) => s.token);
  const username = useAuthStore((s) => s.username);

  const twin = useQuery({ queryKey: ["me-twin"], queryFn: () => studentApi.digitalTwin(token!), enabled: !!token });
  const career = useQuery({ queryKey: ["me-career"], queryFn: () => studentApi.careerReadiness(token!), enabled: !!token });
  const weaknesses = useQuery({ queryKey: ["me-weak"], queryFn: () => studentApi.weaknesses(token!), enabled: !!token });
  const progress = useQuery({ queryKey: ["me-progress"], queryFn: () => studentApi.progress(token!), enabled: !!token });
  const recos = useQuery({ queryKey: ["me-recos"], queryFn: () => studentApi.recommendations(token!), enabled: !!token });

  const isLoading = twin.isLoading || career.isLoading || weaknesses.isLoading;

  const riskTone = twin.data?.health.risk_level === "high" ? "destructive" : twin.data?.health.risk_level === "medium" ? "warning" : "success";

  return (
    <div className="relative flex flex-col gap-8 overflow-hidden">
      <div className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-violet-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -left-32 top-40 h-72 w-72 rounded-full bg-sky-500/10 blur-3xl" />

      {/* ── Hero ────────────────────────────────────────────── */}
      <section
        className="fade-up relative overflow-hidden rounded-3xl border border-[var(--border)] bg-gradient-to-br from-violet-500/10 via-white/80 to-white p-6 backdrop-blur"
        style={{ "--d": "0ms" } as React.CSSProperties}
      >
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-violet-500/5 blur-2xl" />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <Badge tone="primary" className="mb-2">MY INSIGHTS</Badge>
            <h1 className="text-2xl font-extrabold tracking-tight md:text-3xl">
              {greeting()}, {username}
            </h1>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              {twin.data
                ? `${twin.data.student_id} \u00b7 ${twin.data.identity.program} \u00b7 Year ${twin.data.identity.year}`
                : "Your academic insights — digital twin, career readiness and progress"}
            </p>
          </div>
          {twin.data && (
            <div className="flex flex-wrap gap-2">
              <Badge tone={riskTone}>
                {twin.data.health.risk_level.toUpperCase()} RISK
              </Badge>
              <Badge tone={trendTone(twin.data.trajectory.trend)} className="capitalize">
                {twin.data.trajectory.trend === "improving" && <TrendingUp className="mr-1 h-3 w-3" />}
                {twin.data.trajectory.trend === "declining" && <TrendingDown className="mr-1 h-3 w-3" />}
                Trajectory: {twin.data.trajectory.trend}
              </Badge>
              <Badge tone="neutral" className="font-mono">
                {twin.data.student_id}
              </Badge>
            </div>
          )}
        </div>
      </section>

      {/* ── Stat Rings ──────────────────────────────────────── */}
      <section
        className="fade-up grid grid-cols-1 gap-4 md:grid-cols-3"
        style={{ "--d": "60ms" } as React.CSSProperties}
      >
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
              <Skeleton className="h-16 w-16 shrink-0 rounded-full" />
              <div className="flex flex-col gap-2">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-8 w-16" />
                <Skeleton className="h-3 w-20" />
              </div>
            </div>
          ))
        ) : (
          <>
            <div className="flex items-center gap-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 transition-all hover:-translate-y-0.5 hover:shadow-md">
              <ProgressRing value={twin.data?.health.success_score ?? 0} color="#10b981" />
              <div className="min-w-0">
                <p className="text-xs text-[var(--muted-foreground)]">Success Score</p>
                <p className="text-3xl font-extrabold">{twin.data?.health.success_score ?? "\u2014"}</p>
                <Badge tone={riskTone} className="mt-0.5">{twin.data?.health.risk_level ?? "\u2014"} risk</Badge>
              </div>
            </div>

            <div className="flex items-center gap-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 transition-all hover:-translate-y-0.5 hover:shadow-md">
              <ProgressRing value={career.data?.career_readiness_score ?? 0} color="#0ea5e9" />
              <div className="min-w-0">
                <p className="text-xs text-[var(--muted-foreground)]">Career Readiness</p>
                <p className="text-3xl font-extrabold">{career.data?.career_readiness_score ?? "\u2014"}</p>
                <Badge tone={career.data?.band === "career_ready" ? "success" : career.data?.band === "building" ? "warning" : "destructive"} className="mt-0.5">
                  {career.data?.band ?? "\u2014"}
                </Badge>
              </div>
            </div>

            <div className="flex items-center gap-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 transition-all hover:-translate-y-0.5 hover:shadow-md">
              <ProgressRing value={100 - (weaknesses.data?.overall_weakness_score ?? 0)} color="#f43f5e" />
              <div className="min-w-0">
                <p className="text-xs text-[var(--muted-foreground)]">Weakness Score</p>
                <p className="text-3xl font-extrabold">{weaknesses.data?.overall_weakness_score ?? "\u2014"}</p>
                <p className="mt-0.5 text-[11px] text-[var(--muted-foreground)]">lower is better</p>
              </div>
            </div>
          </>
        )}
      </section>

      {/* ── Digital Twin ────────────────────────────────────── */}
      <section
        className="fade-up rounded-2xl border border-[var(--border)] bg-gradient-to-br from-violet-500/5 to-transparent p-5"
        style={{ "--d": "120ms" } as React.CSSProperties}
      >
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-violet-600" />
          <h2 className="text-sm font-bold">Your Digital Twin</h2>
        </div>
        {twin.isLoading ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-8 w-48" />
            <div className="grid grid-cols-5 gap-3">
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {/* Stat tiles */}
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              {[
                { label: "GPA", value: twin.data?.identity.gpa, color: "text-violet-600 bg-violet-100" },
                { label: "Attendance", value: twin.data ? `${Math.round(twin.data.behavior.attendance * 100)}%` : "\u2014", color: "text-sky-600 bg-sky-100" },
                { label: "Pass rate", value: twin.data ? `${Math.round(twin.data.behavior.pass_rate * 100)}%` : "\u2014", color: "text-emerald-600 bg-emerald-100" },
                { label: "Credits", value: twin.data?.identity.credits_earned, color: "text-amber-600 bg-amber-100" },
                { label: "Course load", value: twin.data?.identity.course_load, color: "text-indigo-600 bg-indigo-100" },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2.5 rounded-xl border border-[var(--border)] bg-white/60 px-3 py-3">
                  <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg text-[10px] font-bold ${item.color}`}>
                    {item.label.charAt(0)}
                  </span>
                  <div className="min-w-0">
                    <div className="text-[10px] text-[var(--muted-foreground)]">{item.label}</div>
                    <div className="text-lg font-bold">{item.value ?? "\u2014"}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Strengths + Weaknesses + Next actions */}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3">
                <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-emerald-700">
                  <ShieldCheck className="h-3.5 w-3.5" /> Strengths
                </div>
                <ul className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
                  {twin.data?.strengths.map((s) => <li key={s} className="flex items-start gap-1.5"><span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />{s}</li>)}
                </ul>
              </div>
              <div className="rounded-xl border border-red-200 bg-red-50/50 p-3">
                <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-red-700">
                  <TriangleAlert className="h-3.5 w-3.5" /> Watch Areas
                </div>
                <ul className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
                  {twin.data?.weaknesses.map((w) => <li key={w} className="flex items-start gap-1.5"><span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-red-500" />{w}</li>)}
                </ul>
              </div>
              <div className="rounded-xl border border-sky-200 bg-sky-50/50 p-3">
                <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-sky-700">
                  <Lightbulb className="h-3.5 w-3.5" /> Next Best Actions
                </div>
                <ul className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
                  {twin.data?.next_best_actions.map((a) => <li key={a} className="flex items-start gap-1.5"><span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-500" />{a}</li>)}
                </ul>
              </div>
            </div>

            {/* Trajectory reasons */}
            {twin.data && twin.data.trajectory.reasons.length > 0 && (
              <div className="rounded-xl border border-[var(--border)] bg-white/60 p-3">
                <p className="mb-1 text-xs font-semibold text-[var(--muted-foreground)]">Trajectory reasons</p>
                <div className="flex flex-wrap gap-1.5">
                  {twin.data.trajectory.reasons.map((r) => (
                    <span key={r} className="rounded-full border border-[var(--border)] bg-[var(--muted)]/40 px-2.5 py-0.5 text-[10px] text-[var(--muted-foreground)]">{r}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ── Progress Charts ─────────────────────────────────── */}
      <section
        className="fade-up rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5"
        style={{ "--d": "180ms" } as React.CSSProperties}
      >
        <div className="mb-4 flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-[var(--primary)]" />
          <h2 className="text-sm font-bold">Progress over the term</h2>
        </div>
        {progress.isLoading ? (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-64 rounded-lg" />)}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div>
              <p className="mb-2 text-xs font-medium text-[var(--muted-foreground)]">Success score (0–100)</p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chart(progress.data?.success_trend ?? [], (v) => v)}>
                    <defs>
                      <linearGradient id="gradSuccess" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="var(--primary)" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="week" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Area type="monotone" dataKey="value" stroke="var(--primary)" strokeWidth={2} fill="url(#gradSuccess)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium text-[var(--muted-foreground)]">Attendance (%)</p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chart(progress.data?.attendance_trend ?? [], (v) => Math.round(v * 100))}>
                    <defs>
                      <linearGradient id="gradAtt" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="week" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Area type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} fill="url(#gradAtt)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium text-[var(--muted-foreground)]">GPA (0–4)</p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chart(progress.data?.gpa_trend ?? [], (v) => v)}>
                    <defs>
                      <linearGradient id="gradGpa" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="week" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 4]} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Area type="monotone" dataKey="value" stroke="#8b5cf6" strokeWidth={2} fill="url(#gradGpa)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* Course trends table */}
        {progress.data && progress.data.course_trends.length > 0 && (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                  <th className="py-2 pr-4">Course</th>
                  <th className="py-2 pr-4">Pass probability</th>
                  <th className="py-2 pr-4 min-w-[120px]">Probability bar</th>
                  <th className="py-2 pr-4">Risk</th>
                  <th className="py-2 pr-4">Trend</th>
                </tr>
              </thead>
              <tbody>
                {progress.data.course_trends.map((c) => (
                  <tr key={c.course_code} className={cn("border-b border-[var(--border)] border-l-4", riskBorder(c.risk_level ?? "low"))}>
                    <td className="py-2 pr-4 font-medium">
                      {c.course_code} <span className="text-xs font-normal text-[var(--muted-foreground)]">{c.title}</span>
                    </td>
                    <td className="py-2 pr-4 font-semibold">
                      {c.pass_probability != null ? `${Math.round(c.pass_probability * 100)}%` : "\u2014"}
                    </td>
                    <td className="py-2 pr-4">
                      <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--muted)]">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all duration-500",
                            c.risk_level === "high" ? "bg-red-500" : c.risk_level === "medium" ? "bg-amber-500" : "bg-emerald-500"
                          )}
                          style={{ width: `${c.pass_probability != null ? Math.round(c.pass_probability * 100) : 0}%` }}
                        />
                      </div>
                    </td>
                    <td className="py-2 pr-4">
                      <Badge tone={c.risk_level === "high" ? "destructive" : c.risk_level === "medium" ? "warning" : "success"}>
                        {c.risk_level ?? "\u2014"}
                      </Badge>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={cn("inline-flex items-center gap-1 text-xs font-medium capitalize", c.trend === "improving" ? "text-emerald-600" : c.trend === "declining" ? "text-red-600" : "text-[var(--muted-foreground)]")}>
                        {c.trend === "improving" && <TrendingUp className="h-3 w-3" />}
                        {c.trend === "declining" && <TrendingDown className="h-3 w-3" />}
                        {c.trend}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Two-column: Weaknesses + Career ─────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

        {/* Weakness Detection */}
        <section
          className="fade-up rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5"
          style={{ "--d": "240ms" } as React.CSSProperties}
        >
          <div className="mb-4 flex items-center gap-2">
            <TriangleAlert className="h-4 w-4 text-red-500" />
            <h2 className="text-sm font-bold">Weakness detection</h2>
            {weaknesses.data && (
              <Badge tone={weaknesses.data.overall_weakness_score > 50 ? "destructive" : weaknesses.data.overall_weakness_score > 25 ? "warning" : "success"} className="ml-auto">
                Score: {weaknesses.data.overall_weakness_score}
              </Badge>
            )}
          </div>
          {weaknesses.isLoading ? (
            <div className="flex flex-col gap-3">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {(weaknesses.data?.areas ?? []).map((area) => (
                <div key={area.area} className={cn("rounded-xl border border-l-4 p-3", riskBorder(area.severity))}>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold capitalize">{area.area}</span>
                    <Badge tone={area.severity === "high" ? "destructive" : area.severity === "medium" ? "warning" : "neutral"}>
                      {area.severity}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted-foreground)]">{area.detail}</p>
                  {area.courses.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {area.courses.map((c) => (
                        <span key={c.course_code} className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-white/60 px-2 py-0.5 text-[10px] font-medium">
                          <BookOpen className="h-2.5 w-2.5" /> {c.course_code}
                          <span className="text-[var(--muted-foreground)]">· {c.evidence}</span>
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="mt-1.5 text-xs font-medium text-[var(--primary)]">{area.recommendation}</p>
                </div>
              ))}
              {weaknesses.data?.strengths && weaknesses.data.strengths.length > 0 && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3">
                  <p className="mb-1 text-xs font-semibold text-emerald-700">Your strengths</p>
                  <div className="flex flex-wrap gap-1.5">
                    {weaknesses.data.strengths.map((s) => (
                      <span key={s} className="rounded-full border border-emerald-200 bg-white/60 px-2.5 py-0.5 text-[10px] font-medium text-emerald-700">{s}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Career Readiness */}
        <section
          className="fade-up rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5"
          style={{ "--d": "260ms" } as React.CSSProperties}
        >
          <div className="mb-4 flex items-center gap-2">
            <Target className="h-4 w-4 text-sky-600" />
            <h2 className="text-sm font-bold">Career readiness</h2>
          </div>
          {career.isLoading ? (
            <div className="flex flex-col gap-3">
              <Skeleton className="h-20 w-full rounded-lg" />
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-8 rounded-lg" />)}
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-4">
                <ProgressRing value={career.data?.career_readiness_score ?? 0} size={72} stroke={6} color="#0ea5e9" />
                <div className="flex flex-col gap-1">
                  <span className="text-3xl font-extrabold">{career.data?.career_readiness_score ?? "\u2014"}</span>
                  <Badge tone={career.data?.band === "career_ready" ? "success" : career.data?.band === "building" ? "warning" : "destructive"}>
                    {career.data?.band ?? "\u2014"}
                  </Badge>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                {career.data?.components.map((c) => (
                  <div key={c.name} className="text-sm">
                    <div className="flex justify-between">
                      <span className="capitalize">{c.name}</span>
                      <span className="font-semibold">{Math.round(c.score * 100)}%</span>
                    </div>
                    <div className="mt-1 h-2 overflow-hidden rounded-full bg-[var(--muted)]">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-sky-500 to-cyan-500 transition-all duration-500"
                        style={{ width: `${Math.round(c.score * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {career.data && (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {career.data.strengths.length > 0 && (
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3">
                      <p className="mb-1 text-xs font-semibold text-emerald-700">Strengths</p>
                      <ul className="flex flex-col gap-0.5 text-xs text-[var(--muted-foreground)]">
                        {career.data.strengths.map((s) => <li key={s} className="flex items-start gap-1.5"><span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />{s}</li>)}
                      </ul>
                    </div>
                  )}
                  {career.data.areas_to_grow.length > 0 && (
                    <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3">
                      <p className="mb-1 text-xs font-semibold text-amber-700">Areas to grow</p>
                      <ul className="flex flex-col gap-0.5 text-xs text-[var(--muted-foreground)]">
                        {career.data.areas_to_grow.map((a) => <li key={a} className="flex items-start gap-1.5"><span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />{a}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {career.data && career.data.drivers.length > 0 && (
                <div className="rounded-xl border border-[var(--border)] bg-[var(--muted)]/30 p-3">
                  <p className="mb-1 text-xs font-semibold text-[var(--muted-foreground)]">Key drivers</p>
                  <div className="flex flex-wrap gap-1.5">
                    {career.data.drivers.map((d) => (
                      <span key={d} className="rounded-full border border-[var(--border)] bg-white/60 px-2.5 py-0.5 text-[10px] text-[var(--muted-foreground)]">{d}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      {/* ── Recommendations ─────────────────────────────────── */}
      <section
        className="fade-up rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5"
        style={{ "--d": "300ms" } as React.CSSProperties}
      >
        <div className="mb-4 flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          <h2 className="text-sm font-bold">AI Recommendations</h2>
        </div>
        {recos.isLoading ? (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-lg" />)}
          </div>
        ) : recos.data ? (
          <div className="flex flex-col gap-4">
            {/* Elective recommendations */}
            {recos.data.electives.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-violet-700">Recommended electives</p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {recos.data.electives.map((e) => (
                    <div key={e.course_code} className="flex items-start gap-3 rounded-xl border border-[var(--border)] bg-white/60 p-3 transition-all hover:-translate-y-0.5 hover:shadow-md">
                      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-100 text-violet-600">
                        <Award className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold">{e.course_code}</span>
                          <Badge tone="primary">{Math.round(e.match_score * 100)}% match</Badge>
                        </div>
                        <p className="text-xs text-[var(--muted-foreground)]">{e.title}</p>
                        <p className="mt-0.5 text-[10px] text-[var(--muted-foreground)]">{e.department} \u00b7 {e.credits} credits</p>
                        <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">{e.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Strengthen */}
            {recos.data.strengthen.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-700">Courses to strengthen</p>
                <div className="flex flex-col gap-1.5">
                  {recos.data.strengthen.map((s) => (
                    <div key={s.course_code} className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50/50 px-3 py-2">
                      <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                      <div className="min-w-0">
                        <span className="text-xs font-semibold">{s.course_code}</span>
                        <span className="ml-1 text-xs text-[var(--muted-foreground)]">{s.title}</span>
                        <p className="text-[11px] text-[var(--muted-foreground)]">{s.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Next steps */}
            {recos.data.next_steps.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-sky-700">Suggested next steps</p>
                <div className="flex flex-col gap-1.5">
                  {recos.data.next_steps.map((step, i) => (
                    <div key={i} className="flex items-start gap-2 rounded-lg border border-sky-200 bg-sky-50/50 px-3 py-2">
                      <ChevronRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-sky-600" />
                      <span className="text-xs text-[var(--muted-foreground)]">{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-[var(--muted-foreground)]">No recommendations available yet.</p>
        )}
      </section>
    </div>
  );
}


