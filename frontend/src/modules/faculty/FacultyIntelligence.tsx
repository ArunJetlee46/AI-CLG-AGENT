import { useQuery } from "@tanstack/react-query";
import {
  Award,
  Brain,
  CalendarClock,
  FileWarning,
  FlaskConical,
  GraduationCap,
  Sparkles,
  Trophy,
} from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { StatCard } from "@/core/components/StatCard";
import { facultyApi } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";

const TABS = [
  { key: "twin", label: "Digital Twin", icon: Brain },
  { key: "outcomes", label: "Learning Outcomes", icon: GraduationCap },
  { key: "performers", label: "High Performers", icon: Trophy },
  { key: "research", label: "Research", icon: FlaskConical },
  { key: "schedule", label: "Schedule", icon: CalendarClock },
  { key: "interventions", label: "Interventions", icon: FileWarning },
] as const;

type TabKey = (typeof TABS)[number]["key"];

const bandTone = (band: string) =>
  band === "high" || band === "healthy" ? "success" : band === "medium" || band === "warning" ? "warning" : "destructive";

const masteryBar = (value: number) =>
  value >= 75 ? "bg-emerald-500" : value >= 50 ? "bg-amber-500" : "bg-red-500";

export function FacultyIntelligence() {
  const token = useAuthStore((s) => s.token);
  const [tab, setTab] = useState<TabKey>("twin");

  const twin = useQuery({ queryKey: ["fac-twin"], queryFn: () => facultyApi.facultyTwin(token!), enabled: !!token });
  const outcomes = useQuery({ queryKey: ["fac-outcomes"], queryFn: () => facultyApi.learningOutcomes(token!), enabled: !!token });
  const performers = useQuery({ queryKey: ["fac-performers"], queryFn: () => facultyApi.highPerformers(token!), enabled: !!token });
  const research = useQuery({ queryKey: ["fac-research"], queryFn: () => facultyApi.researchRecommendations(token!), enabled: !!token });
  const schedule = useQuery({ queryKey: ["fac-schedule"], queryFn: () => facultyApi.schedule(token!), enabled: !!token });
  const interventions = useQuery({ queryKey: ["fac-interventions"], queryFn: () => facultyApi.interventionRecommendations(token!), enabled: !!token });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Faculty Intelligence" subtitle="Digital twin, outcomes, performers, research, schedule and interventions" icon={Sparkles} accent="bg-violet-100 text-violet-600" />

      <div className="flex flex-wrap gap-1 rounded-xl border border-[var(--border)] bg-[var(--card)] p-1">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors ${tab === key ? "bg-[var(--primary)]/10 font-medium text-[var(--primary)]" : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]"}`}
          >
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
      </div>

      {tab === "twin" && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Avg course health" value={twin.data?.health.avg_course_health ?? "…"} sub="/100" icon={GraduationCap} accent="bg-emerald-100 text-emerald-600" />
            <StatCard label="At-risk students" value={twin.data?.health.at_risk_count ?? "…"} sub="high risk" icon={FileWarning} accent="bg-red-100 text-red-600" />
            <StatCard label="High performers" value={twin.data?.health.high_performers ?? "…"} sub="top of class" icon={Trophy} accent="bg-amber-100 text-amber-600" />
            <StatCard label="Class attendance" value={twin.data ? `${Math.round(twin.data.health.attendance * 100)}%` : "…"} sub="average" icon={CalendarClock} accent="bg-sky-100 text-sky-600" />
          </div>
          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-4 w-4" /> Teaching snapshot
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="neutral" className="font-mono">{twin.data?.staff_id}</Badge>
                <Badge tone={bandTone(twin.data?.trajectory.trend ?? "")}>trajectory: {twin.data?.trajectory.trend ?? "…"}</Badge>
                <span className="rounded-full border border-[var(--border)] px-2 py-0.5 text-xs text-[var(--muted-foreground)]">
                  {twin.data?.identity.department}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {[
                  { label: "Courses", value: twin.data?.identity.courses },
                  { label: "Students", value: twin.data?.identity.students },
                  { label: "Hours / week", value: twin.data?.identity.teaching_hours },
                  { label: "Capacity", value: twin.data?.identity.max_hours },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/40 px-3 py-2">
                    <div className="text-[11px] text-[var(--muted-foreground)]">{label}</div>
                    <div className="text-lg font-semibold">{value ?? "…"}</div>
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
              <div className="rounded-lg border-l-4 border-[var(--primary)] bg-[var(--primary)]/5 px-3 py-2 text-sm">
                <span className="font-semibold">Next actions:</span> {twin.data?.next_best_actions.join(" · ")}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {tab === "outcomes" && (
        <div className="flex flex-col gap-4">
          {outcomes.data?.courses.map((c) => (
            <Card key={c.course_code} className="card-shell">
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-sm">
                  <span>
                    {c.course_code} <span className="font-normal text-[var(--muted-foreground)]">{c.title} · {c.enrolled} students</span>
                  </span>
                  <Badge tone="neutral" className="capitalize">weakest: {c.weakest_area}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap gap-2 text-xs">
                    {(["high", "medium", "low"] as const).map((b) => (
                      <span key={b} className="rounded-full border border-[var(--border)] px-2 py-0.5 text-[var(--muted-foreground)]">
                        {b}: {c.distribution[b]}
                      </span>
                    ))}
                  </div>
                  {c.outcomes.map((o) => (
                    <div key={o.area}>
                      <div className="flex justify-between text-sm">
                        <span className="capitalize font-medium">{o.area}</span>
                        <span className="text-[var(--muted-foreground)]">{o.mastery.toFixed(1)}%</span>
                      </div>
                      <div className="mt-1 h-2 overflow-hidden rounded-full bg-[var(--muted)]">
                        <div className={`h-full ${masteryBar(o.mastery)}`} style={{ width: `${o.mastery}%` }} />
                      </div>
                      <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">{o.detail}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
          {!outcomes.data?.courses.length && <p className="text-sm text-[var(--muted-foreground)]">No outcomes available for your courses yet.</p>}
        </div>
      )}

      {tab === "performers" && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><Trophy className="h-4 w-4" /> High performers</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {performers.data?.map((p, i) => (
              <div key={p.student_id} className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--border)] px-3 py-2">
                <span className="grid h-7 w-7 place-items-center rounded-full bg-amber-100 text-xs font-bold text-amber-700">{i + 1}</span>
                <span className="font-mono text-sm font-semibold">{p.student_id}</span>
                <span className="text-xs text-[var(--muted-foreground)]">GPA {p.gpa} · {p.avg_marks ?? "—"} marks · {Math.round(p.attendance_rate * 100)}%</span>
                <Badge tone={bandTone(p.band)} className="ml-auto">score {p.score}</Badge>
                <p className="w-full text-xs text-[var(--muted-foreground)]">{p.reasons.join(" · ")}</p>
              </div>
            ))}
            {!performers.data?.length && <p className="text-sm text-[var(--muted-foreground)]">No performers yet.</p>}
          </CardContent>
        </Card>
      )}

      {tab === "research" && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><FlaskConical className="h-4 w-4" /> Research student recommendations</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {research.data?.candidates.map((c) => (
              <div key={c.student_id} className="rounded-lg border border-[var(--border)] p-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold">{c.student_id}</span>
                  <Badge tone="success">{c.suggested_area}</Badge>
                </div>
                <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                  GPA {c.gpa} · avg marks {c.avg_marks ?? "—"} · courses: {c.courses.join(", ")}
                </p>
                <p className="mt-1 text-xs">{c.rationale}</p>
              </div>
            ))}
            {!research.data?.candidates.length && <p className="text-sm text-[var(--muted-foreground)]">No research-ready candidates yet.</p>}
          </CardContent>
        </Card>
      )}

      {tab === "schedule" && schedule.data && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Hours / week" value={schedule.data.total_hours} sub={`${schedule.data.sessions} sessions`} icon={CalendarClock} accent="bg-violet-100 text-violet-600" />
            <StatCard label="Capacity" value={schedule.data.max_hours} sub="weekly cap" icon={Award} accent="bg-sky-100 text-sky-600" />
            <StatCard label="Utilization" value={`${schedule.data.utilization}%`} sub="of capacity" icon={GraduationCap} accent="bg-emerald-100 text-emerald-600" />
            <StatCard label="Load status" value={schedule.data.overloaded ? "OVER" : "OK"} sub={schedule.data.overloaded ? "over capacity" : "within cap"} icon={FileWarning} accent={schedule.data.overloaded ? "bg-red-100 text-red-600" : "bg-emerald-100 text-emerald-600"} />
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {schedule.data.days.map((d) => (
              <Card key={d.day} className="card-shell">
                <CardHeader>
                  <CardTitle className="text-sm">{d.day}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-1.5">
                  {d.slots.map((s) => (
                    <div key={`${s.course_code}-${s.start}`} className="flex items-center justify-between rounded-md border border-[var(--border)] px-3 py-1.5 text-sm">
                      <span>
                        <span className="font-medium">{s.course_code}</span>{" "}
                        <span className="text-xs text-[var(--muted-foreground)]">{s.title}</span>
                      </span>
                      <span className="text-xs text-[var(--muted-foreground)]">{s.start}–{s.end} ({s.hours}h)</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
          </div>
          <p className="rounded-lg border-l-4 border-[var(--primary)] bg-[var(--primary)]/5 px-3 py-2 text-sm">{schedule.data.advisory}</p>
        </div>
      )}

      {tab === "interventions" && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><FileWarning className="h-4 w-4" /> Automated intervention recommendations</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {interventions.data?.map((r) => (
              <div key={`${r.student_id}-${r.course_code}`} className="rounded-lg border border-[var(--border)] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-semibold">{r.student_id}</span>
                  <Badge tone="neutral">{r.course_code}</Badge>
                  <Badge tone={bandTone(r.risk_level)} className="ml-auto">
                    {r.risk_level} · {Math.round(r.probability * 100)}%
                  </Badge>
                </div>
                <p className="mt-1 text-xs font-medium text-[var(--primary)]">{r.proposed_action}</p>
                <ul className="mt-1 list-inside list-disc text-xs text-[var(--muted-foreground)]">
                  {r.recommendation.map((a) => <li key={a}>{a}</li>)}
                </ul>
              </div>
            ))}
            {!interventions.data?.length && <p className="text-sm text-[var(--muted-foreground)]">No interventions recommended right now.</p>}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
