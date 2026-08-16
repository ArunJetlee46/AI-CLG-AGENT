import { useMutation, useQuery } from "@tanstack/react-query";
import { FlaskConical, TrendingDown, TrendingUp, TriangleAlert, Waves } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { Skeleton } from "@/core/components/ui/skeleton";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi, type ScenarioResult } from "@/modules/admin/api";

const trajectoryStyles: Record<string, string> = {
  improving: "text-green-600",
  stable: "text-amber-600",
  declining: "text-red-600",
};

export function AdminDigitalTwin() {
  const token = useAuthStore((s) => s.token);
  const [att, setAtt] = useState(0);
  const [pass, setPass] = useState(0);
  const [place, setPlace] = useState(0);
  const [ready, setReady] = useState(0);
  const [interventions, setInterventions] = useState(0);
  const [scenario, setScenario] = useState<ScenarioResult | null>(null);

  const twin = useQuery({ queryKey: ["admin-twin"], queryFn: () => adminApi.digitalTwin(token!), enabled: !!token, refetchInterval: 60_000 });

  const run = useMutation({
    mutationFn: () =>
      adminApi.runScenario(
        {
          attendance_delta: att,
          pass_rate_delta: pass,
          placement_delta: place,
          readiness_delta: ready,
          interventions,
        },
        token!
      ),
    onSuccess: setScenario,
  });

  const d = twin.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="University Digital Twin" subtitle="Live virtual replica of the campus — model what-if scenarios" icon={Waves} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Health score</CardTitle>
          </CardHeader>
          <CardContent>
            {twin.isLoading && !d ? (
              <Skeleton className="h-9 w-16" />
            ) : (
              <p className={`text-4xl font-bold ${trajectoryStyles[d?.trajectory ?? "stable"]}`}>
                {d?.health.university_health_score ?? "—"}
              </p>
            )}
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">trajectory: {d?.trajectory}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>People</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {twin.isLoading && !d ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-4 w-24" />
              </div>
            ) : (
              <>
                <p><strong>{d?.entities.students ?? "—"}</strong> students</p>
                <p><strong>{d?.entities.faculty ?? "—"}</strong> faculty</p>
                <p><strong>{d?.entities.courses ?? "—"}</strong> courses</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Infrastructure</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {twin.isLoading && !d ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-4 w-36" />
                <Skeleton className="h-4 w-24" />
              </div>
            ) : (
              <>
                <p><strong>{d?.entities.rooms ?? "—"}</strong> rooms</p>
                <p><strong>{d?.entities.timetable_entries ?? "—"}</strong> timetable slots</p>
                <p>{d?.state.pending_approvals ?? 0} pending approvals</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>KPI snapshot</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {twin.isLoading && !d ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-24" />
              </div>
            ) : (
              <>
                <p>Attendance <strong>{d?.state.kpis.attendance}%</strong></p>
                <p>Success <strong>{d?.state.kpis.academic_success}%</strong></p>
                <p>Placement <strong>{d?.state.kpis.placement}%</strong></p>
                <p>At-risk <strong>{d?.state.kpis.at_risk}%</strong></p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Subsystems</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {(d?.subsystems ?? []).map((s) => (
            <div key={s.key} className="flex items-center gap-2 border-b border-[var(--border)] pb-2 text-sm">
              <span className="w-36">{s.label}</span>
              <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${s.score}%` }} />
              </span>
              <span className="w-8 text-right font-semibold">{s.score}</span>
              <span className={`flex w-24 items-center gap-1 ${trajectoryStyles[s.trajectory]}`}>
                {s.trajectory === "improving" ? <TrendingUp className="h-3.5 w-3.5" /> : s.trajectory === "declining" ? <TrendingDown className="h-3.5 w-3.5" /> : <FlaskConical className="h-3.5 w-3.5" />}
                {s.trajectory}
              </span>
              <span className="text-xs text-[var(--muted-foreground)]">w {s.weight}%</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TriangleAlert className="h-4 w-4" /> What-if simulator
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <label className="flex items-center gap-2 text-sm">
              <span className="w-44">Attendance delta (pp)</span>
              <Input type="number" value={att} onChange={(e) => setAtt(Number(e.target.value))} className="w-24" />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <span className="w-44">Pass rate delta (pp)</span>
              <Input type="number" value={pass} onChange={(e) => setPass(Number(e.target.value))} className="w-24" />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <span className="w-44">Placement delta (pp)</span>
              <Input type="number" value={place} onChange={(e) => setPlace(Number(e.target.value))} className="w-24" />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <span className="w-44">Readiness delta (pp)</span>
              <Input type="number" value={ready} onChange={(e) => setReady(Number(e.target.value))} className="w-24" />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <span className="w-44">High-risk students rescued</span>
              <Input type="number" value={interventions} onChange={(e) => setInterventions(Number(e.target.value))} className="w-24" />
            </label>
            <Button disabled={run.isPending} onClick={() => run.mutate()}>
              <Waves className="h-4 w-4" /> Simulate Scenario
            </Button>
          </CardContent>
        </Card>

        {scenario && (
          <Card>
            <CardHeader>
              <CardTitle>Projected outcome</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div className="flex items-center gap-4">
                <div className="rounded-xl bg-[var(--muted)] px-4 py-3">
                  <p className="text-xs text-[var(--muted-foreground)]">Baseline</p>
                  <p className="text-3xl font-bold">{scenario.baseline.university_health_score}</p>
                </div>
                <span className="text-xl font-bold text-[var(--muted-foreground)]">→</span>
                <div className="rounded-xl bg-green-50 px-4 py-3">
                  <p className="text-xs text-green-700">Projected</p>
                  <p className="text-3xl font-bold text-green-700">{scenario.projected.university_health_score}</p>
                </div>
                <span className={`ml-auto text-lg font-bold ${scenario.impact.score_delta >= 0 ? "text-green-600" : "text-red-600"}`}>
                  {scenario.impact.score_delta >= 0 ? "+" : ""}{scenario.impact.score_delta}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                {Object.entries(scenario.impact.per_axis_deltas).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-2 text-sm">
                    <span className="w-36 capitalize">{k.replace(/_/g, " ")}</span>
                    <span className={`font-semibold ${v >= 0 ? "text-green-600" : "text-red-600"}`}>
                      {v >= 0 ? "+" : ""}{v}
                    </span>
                  </div>
                ))}
              </div>
              <ul className="flex list-disc flex-col gap-1 pl-5 text-xs text-[var(--muted-foreground)]">
                {scenario.assumptions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active signals</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {(d?.warnings ?? []).map((w) => (
            <div key={w.id} className="flex items-start gap-2 border-b border-[var(--border)] pb-2 text-sm">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
              <div>
                <p className="font-medium">{w.title}</p>
                <p className="text-xs text-[var(--muted-foreground)]">{w.detail}</p>
              </div>
            </div>
          ))}
          {(d?.warnings ?? []).length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No active signals.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
