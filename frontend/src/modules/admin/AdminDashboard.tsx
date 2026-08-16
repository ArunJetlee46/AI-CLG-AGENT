import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, AlertTriangle, Bot, Building2, GraduationCap, Power, ShieldCheck, Users } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { EmptyState } from "@/core/components/ui/empty-state";
import { StatCardSkeleton } from "@/core/components/ui/skeleton";
import { toast } from "@/core/components/ui/toast";
import { adminApi } from "@/modules/admin/api";
import { useAuthStore } from "@/core/stores/auth";

const severityStyles: Record<string, string> = {
  critical: "bg-red-600 text-white",
  important: "bg-orange-500 text-white",
  warning: "bg-yellow-500 text-black",
};

export function AdminDashboard() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();

  const cc = useQuery({ queryKey: ["admin-cc"], queryFn: () => adminApi.commandCenter(token!), enabled: !!token, refetchInterval: 60_000 });
  const score = useQuery({ queryKey: ["admin-score"], queryFn: () => adminApi.healthScore(token!), enabled: !!token, refetchInterval: 60_000 });
  const warnings = useQuery({ queryKey: ["admin-warnings"], queryFn: () => adminApi.earlyWarnings(token!), enabled: !!token, refetchInterval: 60_000 });
  const depts = useQuery({ queryKey: ["admin-depts"], queryFn: () => adminApi.departments(token!), enabled: !!token });
  const workload = useQuery({ queryKey: ["admin-workload"], queryFn: () => adminApi.facultyWorkload(token!, 8), enabled: !!token });
  const agents = useQuery({ queryKey: ["admin-agents"], queryFn: () => adminApi.agents(token!), enabled: !!token });
  const safety = useQuery({ queryKey: ["admin-safety"], queryFn: () => adminApi.safety(token!), enabled: !!token, refetchInterval: 60_000 });

  const setSafety = useMutation({
    mutationFn: (body: { execution_enabled: boolean; read_only: boolean }) => adminApi.setSafety(body, token!),
    onSuccess: (_, body) => {
      toast.success(
        body.execution_enabled ? "AI Execution resumed" : "AI Execution paused",
        body.execution_enabled ? "Agents may now act on the campus." : "Agents will reject every write at the source."
      );
      queryClient.invalidateQueries({ queryKey: ["admin-safety"] });
      queryClient.invalidateQueries({ queryKey: ["admin-cc"] });
      queryClient.invalidateQueries({ queryKey: ["admin-agents"] });
      queryClient.invalidateQueries({ queryKey: ["admin-score"] });
    },
    onError: () => toast.error("Failed to update safety settings"),
  });

  const ov = cc.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="University Command Center"
        subtitle="Live institutional health, governance and AI operations"
        icon={ShieldCheck}
        actions={
          <div
            className={`flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${
              safety.data?.execution_allowed ? "bg-green-100 text-green-700" : "bg-red-600 text-white"
            }`}
          >
            <Power className="h-4 w-4" />
            AI Execution {safety.data?.execution_allowed ? "ENABLED" : "PAUSED"}
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {ov ? (
          <>
            <StatCard label="Students" value={ov.counts.students} sub={`${ov.counts.departments ?? "—"} departments`} icon={GraduationCap} accent="bg-sky-100 text-sky-600" />
            <StatCard label="Faculty" value={ov.counts.faculty} sub={`${ov.counts.courses ?? "—"} courses`} icon={Users} accent="bg-violet-100 text-violet-600" />
            <StatCard label="Institutional KPIs" value={`${ov.kpis.academic_success ?? "—"}%`} sub={`attendance ${ov.kpis.attendance ?? "—"}% · placement ${ov.kpis.placement ?? "—"}%`} icon={Activity} accent="bg-emerald-100 text-emerald-600" />
            <StatCard label="At-risk students" value={`${ov.kpis.at_risk ?? "—"}%`} sub={`${ov.pending_approvals ?? "—"} pending approvals · ${ov.active_agents ?? "—"} agents`} icon={AlertTriangle} accent="bg-red-100 text-red-600" />
          </>
        ) : (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>University Health Score</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-5xl font-bold text-[var(--primary)]">{score.data?.university_health_score ?? "—"}</p>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">composite of 5 weighted axes</p>
            <div className="mt-4 flex flex-col gap-2">
              {(score.data
                ? Object.entries(score.data.axes).map(([k, v]) => ({ k, v }))
                : []
              ).map(({ k, v }) => (
                <div key={k} className="flex items-center gap-2 text-sm">
                  <span className="w-32 capitalize">{k.replace("_", " ")}</span>
                  <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                    <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${v}%` }} />
                  </span>
                  <span className="w-8 text-right">{v}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-4 w-4" /> AI Agent Control Center
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {(agents.data ?? []).map((a) => (
              <div key={a.name} className="flex items-center gap-2 border-b border-[var(--border)] pb-2 text-sm">
                <span className="h-2 w-2 shrink-0 rounded-full bg-green-500" />
                <span className="w-40 font-medium">{a.name}</span>
                <span className="text-xs text-[var(--muted-foreground)]">{a.role}</span>
                <span className="ml-auto flex items-center gap-3 text-xs text-[var(--muted-foreground)]">
                  <span>{a.tasks_processed} tasks</span>
                  <span className={a.status === "paused" ? "font-semibold text-red-600" : ""}>{a.status}</span>
                  {a.last_activity && <span>{new Date(a.last_activity).toLocaleTimeString()}</span>}
                </span>
              </div>
            ))}
            {(agents.data ?? []).length === 0 && (
              <EmptyState title="No agents running" description="Agent activity will appear here once agents process tasks." icon={Bot} />
            )}
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Button
                loading={setSafety.isPending}
                variant={safety.data?.execution_allowed ? "destructive" : "default"}
                onClick={() => setSafety.mutate({ execution_enabled: !safety.data?.execution_allowed, read_only: false })}
              >
                {safety.data?.execution_allowed ? "PAUSE EXECUTION" : "RESUME EXECUTION"}
              </Button>
              <Button
                loading={setSafety.isPending}
                variant="outline"
                onClick={() => setSafety.mutate({ execution_enabled: true, read_only: !safety.data?.read_only })}
              >
                {safety.data?.read_only ? "READ-ONLY MODE: ON" : "READ-ONLY MODE: OFF"}
              </Button>
              <p className="text-xs text-[var(--muted-foreground)]">
                While paused, the Execute Agent rejects every write at the source.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> University Early Warning System
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {(warnings.data ?? []).map((w) => (
              <div key={w.id} className="flex items-start gap-2 border-b border-[var(--border)] pb-2 text-sm">
                <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${severityStyles[w.severity]}`}>
                  {w.severity.toUpperCase()}
                </span>
                <div className="min-w-0">
                  <p className="font-medium">{w.title}</p>
                  <p className="text-xs text-[var(--muted-foreground)]">{w.detail}</p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    <strong>Recommendation:</strong> {w.recommendation}
                  </p>
                </div>
              </div>
            ))}
            {(warnings.data ?? []).length === 0 && (
              <EmptyState title="No warnings" description="No institutional warnings detected." icon={AlertTriangle} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-4 w-4" /> Department Intelligence
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="table-shell">
                <thead>
                  <tr>
                    <th>Department</th>
                    <th className="text-right">Students</th>
                    <th className="text-right">Pass</th>
                    <th className="text-right">Readiness</th>
                    <th className="text-right">Placement</th>
                    <th className="text-right">Health</th>
                  </tr>
                </thead>
                <tbody>
                  {(depts.data?.departments ?? []).map((d) => (
                    <tr key={d.program}>
                      <td>
                        <span className="line-clamp-1 max-w-[180px] font-medium">{d.program}</span>
                        {d.flag && <span className="text-xs text-red-600">⚠ {d.flag}</span>}
                      </td>
                      <td className="text-right">{d.students}</td>
                      <td className="text-right">{d.pass_rate}%</td>
                      <td className="text-right">{d.avg_readiness}</td>
                      <td className="text-right">{d.placement}%</td>
                      <td className="text-right font-semibold">{d.health}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(depts.data?.departments ?? []).length === 0 && (
                <EmptyState title="No departments" description="Department data will appear once analytics run." icon={Building2} className="mt-2" />
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Faculty workload (top by teaching hours)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="table-shell">
              <thead>
                <tr>
                  <th>Staff</th>
                  <th>Department</th>
                  <th className="text-right">Courses</th>
                  <th className="text-right">Students</th>
                  <th className="text-right">Hours</th>
                  <th className="text-right">Utilization</th>
                </tr>
              </thead>
              <tbody>
                {(workload.data ?? []).map((w) => (
                  <tr key={w.staff_id}>
                    <td className="font-medium">{w.staff_id}</td>
                    <td>{w.department}</td>
                    <td className="text-right">{w.course_count}</td>
                    <td className="text-right">{w.student_count}</td>
                    <td className="text-right">{w.teaching_hours}</td>
                    <td className="text-right">{w.utilization}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(workload.data ?? []).length === 0 && (
              <EmptyState title="No workload data" description="Faculty teaching hours will appear here." icon={Users} className="mt-2" />
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
