import { useQuery } from "@tanstack/react-query";
import {
  Award,
  BookOpen,
  CheckCircle2,
  Compass,
  Lock,
  Medal,
  Trophy,
  Users,
} from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { cn } from "@/core/lib/utils";
import { studentApi } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";

const severityTone = (severity: string) =>
  severity === "high" ? "destructive" : severity === "medium" ? "warning" : "neutral";

export function Community() {
  const token = useAuthStore((s) => s.token);

  const gam = useQuery({ queryKey: ["me-gam"], queryFn: () => studentApi.gamification(token!), enabled: !!token });
  const reco = useQuery({ queryKey: ["me-reco"], queryFn: () => studentApi.recommendations(token!), enabled: !!token });
  const groups = useQuery({ queryKey: ["me-groups"], queryFn: () => studentApi.studyGroups(token!), enabled: !!token });
  const notes = useQuery({ queryKey: ["me-notes"], queryFn: () => studentApi.notifications(token!), enabled: !!token });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="My Community & Motivation" subtitle="Recommendations, study partners, badges and notifications" icon={Trophy} accent="bg-amber-100 text-amber-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Medal className="h-4 w-4" /> Your journey
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center gap-6">
            <div className="grid h-20 w-20 place-items-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-md">
              <div className="text-center leading-tight">
                <div className="text-3xl font-extrabold">{gam.data?.level ?? "…"}</div>
                <div className="text-[10px] font-medium uppercase">Level</div>
              </div>
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-semibold">{gam.data?.xp ?? 0} XP</span>
                <span className="text-[var(--muted-foreground)]">{gam.data?.xp_to_next_level ?? "…"} XP to level {(gam.data?.level ?? 0) + 1}</span>
              </div>
              <div className="mt-1.5 h-2.5 overflow-hidden rounded-full bg-[var(--muted)]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-500"
                  style={{ width: `${Math.round((gam.data?.level_progress ?? 0) * 100)}%` }}
                />
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {gam.data?.badges.map((badge) => (
              <div
                key={badge.id}
                title={badge.description}
                className={cn(
                  "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs",
                  badge.earned
                    ? "border-amber-300 bg-amber-50 font-medium text-amber-700"
                    : "border-[var(--border)] bg-[var(--muted)] text-[var(--muted-foreground)]"
                )}
              >
                {badge.earned ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Lock className="h-3.5 w-3.5" />}
                {badge.name}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Compass className="h-4 w-4" /> Course recommendations
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {reco.data?.electives.map((e) => (
              <div key={e.course_code} className="flex items-start justify-between gap-3 rounded-lg border border-[var(--border)] p-3">
                <div>
                  <p className="text-sm font-semibold">
                    {e.course_code} <span className="font-normal text-[var(--muted-foreground)]">· {e.credits} cr</span>
                  </p>
                  <p className="text-xs text-[var(--muted-foreground)]">{e.title} · {e.department}</p>
                  <p className="mt-1 text-xs text-[var(--primary)]">{e.reason}</p>
                </div>
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                  {e.match_score.toFixed(1)}
                </span>
              </div>
            ))}
            {reco.data?.strengthen.map((s) => (
              <div key={s.course_code} className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs">
                <BookOpen className="h-4 w-4 shrink-0 text-red-600" />
                <span>
                  <strong>{s.course_code}</strong> — {s.title}. <span className="text-[var(--muted-foreground)]">{s.reason}</span>
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-4 w-4" /> Study group matches
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {groups.data?.groups.map((g) => (
              <div key={g.peer_student_id} className="rounded-lg border border-[var(--border)] p-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold">{g.peer_student_id}</span>
                  <Badge tone="neutral">
                    {g.peer_program} · GPA {g.peer_gpa}
                  </Badge>
                </div>
                <ul className="mt-1.5 list-inside list-disc text-xs text-[var(--muted-foreground)]">
                  {g.synergy.map((s) => <li key={s}>{s}</li>)}
                </ul>
                <p className="mt-1.5 text-xs">
                  Shared: {g.shared_courses.map((c) => c.course_code).join(", ")} · complementarity {g.complementarity_score.toFixed(1)}
                </p>
              </div>
            ))}
            {!groups.data?.groups.length && (
              <p className="text-sm text-[var(--muted-foreground)]">{groups.data?.note ?? "Looking for matches…"}</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Award className="h-4 w-4" /> Smart notifications
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {notes.data?.notifications.map((n, i) => (
            <div
              key={i}
              className={cn(
                "rounded-lg border border-l-4 px-3 py-2 text-sm",
                n.severity === "high"
                  ? "border-l-red-500 bg-red-50"
                  : n.severity === "medium"
                    ? "border-l-amber-500 bg-amber-50"
                    : "border-l-green-500 bg-green-50"
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{n.title}</span>
                <Badge tone={severityTone(n.severity)}>{n.severity}</Badge>
              </div>
              <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">{n.detail}</p>
              <p className="mt-0.5 text-xs">{n.action}</p>
            </div>
          ))}
          {!notes.data?.notifications.length && <p className="text-sm text-[var(--muted-foreground)]">No notifications yet.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
