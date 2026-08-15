import { useQuery } from "@tanstack/react-query";
import { Brain, Sparkles, Target, TrendingUp, TriangleAlert } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Badge } from "@/core/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { studentApi } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";

const trendTone = (trend: string) =>
  trend === "improving"
    ? "success"
    : trend === "declining"
      ? "destructive"
      : "neutral";

export function Insights() {
  const token = useAuthStore((s) => s.token);

  const twin = useQuery({ queryKey: ["me-twin"], queryFn: () => studentApi.digitalTwin(token!), enabled: !!token });
  const career = useQuery({ queryKey: ["me-career"], queryFn: () => studentApi.careerReadiness(token!), enabled: !!token });
  const weaknesses = useQuery({ queryKey: ["me-weak"], queryFn: () => studentApi.weaknesses(token!), enabled: !!token });
  const progress = useQuery({ queryKey: ["me-progress"], queryFn: () => studentApi.progress(token!), enabled: !!token });

  const chart = (points: { week: number; value: number }[], scale: (v: number) => number) =>
    points.map((p) => ({ week: `W${p.week}`, value: scale(p.value) }));

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="My Insights" subtitle="Digital twin, career readiness, weaknesses and progress" icon={Brain} accent="bg-violet-100 text-violet-600" />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard label="Success score" value={twin.data?.health.success_score ?? "…"} sub={`risk ${twin.data?.health.risk_level ?? "…"}`} icon={Sparkles} accent="bg-emerald-100 text-emerald-600" />
        <StatCard label="Career readiness" value={career.data?.career_readiness_score ?? "…"} sub={`band ${career.data?.band ?? "…"}`} icon={Target} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Weakness score" value={weaknesses.data?.overall_weakness_score ?? "…"} sub="lower is better" icon={TriangleAlert} accent="bg-red-100 text-red-600" />
      </div>

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" /> Your Digital Twin
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={trendTone(twin.data?.trajectory.trend ?? "")}>
              Trajectory: {twin.data?.trajectory.trend ?? "…"}
            </Badge>
            <Badge tone="neutral" className="font-mono">
              {twin.data?.student_id}
            </Badge>
            <span className="rounded-full border border-[var(--border)] px-2 py-0.5 text-xs text-[var(--muted-foreground)]">
              {twin.data?.identity.program} · Year {twin.data?.identity.year}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {[
              { label: "GPA", value: twin.data?.identity.gpa },
              { label: "Attendance", value: twin.data ? `${Math.round(twin.data.behavior.attendance * 100)}%` : "…" },
              { label: "Pass rate", value: twin.data ? `${Math.round(twin.data.behavior.pass_rate * 100)}%` : "…" },
              { label: "Credits", value: twin.data?.identity.credits_earned },
              { label: "Course load", value: twin.data?.identity.course_load },
            ].map((item) => (
              <div key={item.label} className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/40 px-3 py-2">
                <div className="text-[11px] text-[var(--muted-foreground)]">{item.label}</div>
                <div className="text-lg font-semibold">{item.value ?? "…"}</div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-600">Strengths</p>
              <ul className="list-inside list-disc text-sm text-[var(--muted-foreground)]">
                {twin.data?.strengths.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-red-600">Watch areas</p>
              <ul className="list-inside list-disc text-sm text-[var(--muted-foreground)]">
                {twin.data?.weaknesses.map((w) => <li key={w}>{w}</li>)}
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> Progress over the term
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div>
              <p className="mb-2 text-xs font-medium text-[var(--muted-foreground)]">Success score (0-100)</p>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chart(progress.data?.success_trend ?? [], (v) => v)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="week" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="var(--primary)" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium text-[var(--muted-foreground)]">Attendance (%)</p>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chart(progress.data?.attendance_trend ?? [], (v) => Math.round(v * 100))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="week" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium text-[var(--muted-foreground)]">GPA (0-4)</p>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chart(progress.data?.gpa_trend ?? [], (v) => v)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="week" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 4]} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                  <th className="py-2 pr-4">Course</th>
                  <th className="py-2 pr-4">Pass probability</th>
                  <th className="py-2 pr-4">Risk</th>
                  <th className="py-2 pr-4">Attendance trend</th>
                </tr>
              </thead>
              <tbody>
                {progress.data?.course_trends.map((c) => (
                  <tr key={c.course_code} className="border-b border-[var(--border)]">
                    <td className="py-2 pr-4 font-medium">
                      {c.course_code} <span className="text-xs font-normal text-[var(--muted-foreground)]">{c.title}</span>
                    </td>
                    <td className="py-2 pr-4">{c.pass_probability != null ? `${Math.round(c.pass_probability * 100)}%` : "—"}</td>
                    <td className="py-2 pr-4">
                      <Badge tone={c.risk_level === "high" ? "destructive" : c.risk_level === "medium" ? "warning" : "success"}>
                        {c.risk_level ?? "—"}
                      </Badge>
                    </td>
                    <td className="py-2 pr-4 capitalize">{c.trend}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TriangleAlert className="h-4 w-4" /> Weakness detection
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {weaknesses.data?.areas.map((area) => (
              <div key={area.area} className="rounded-lg border border-[var(--border)] p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold capitalize">{area.area}</span>
                  <Badge tone={area.severity === "high" ? "destructive" : area.severity === "medium" ? "warning" : "neutral"}>
                    {area.severity}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-[var(--muted-foreground)]">{area.detail}</p>
                <p className="mt-1 text-xs">{area.recommendation}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-4 w-4" /> Career readiness
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center gap-4">
              <span className="text-4xl font-bold">{career.data?.career_readiness_score ?? "…"}</span>
              <div className="flex flex-col gap-1">
                <Badge tone={career.data?.band === "career_ready" ? "success" : career.data?.band === "building" ? "warning" : "destructive"}>
                  {career.data?.band ?? "…"}
                </Badge>
                <span className="text-xs text-[var(--muted-foreground)]">/ 100</span>
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              {career.data?.components.map((c) => (
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
              {career.data?.drivers.map((d) => <li key={d}>{d}</li>)}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
