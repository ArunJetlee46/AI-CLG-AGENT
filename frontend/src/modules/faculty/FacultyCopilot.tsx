import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bot, FileWarning, FlaskConical, GraduationCap, Landmark, ScrollText, ShieldCheck, Sparkles, Users, Workflow } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { facultyApi } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";

const STAGE_ICONS: Record<string, { icon: typeof Bot; accent: string }> = {
  faculty: { icon: Users, accent: "bg-sky-100 text-sky-600" },
  copilot: { icon: Bot, accent: "bg-violet-100 text-violet-600" },
  data: { icon: GraduationCap, accent: "bg-emerald-100 text-emerald-600" },
  analysis: { icon: Sparkles, accent: "bg-amber-100 text-amber-600" },
  recommendation: { icon: FileWarning, accent: "bg-orange-100 text-orange-600" },
  approval: { icon: ShieldCheck, accent: "bg-red-100 text-red-600" },
  execute: { icon: Workflow, accent: "bg-pink-100 text-pink-600" },
  audit: { icon: ScrollText, accent: "bg-slate-200 text-slate-700" },
};

const stageLink = (key: string) => {
  switch (key) {
    case "recommendation":
      return "/faculty/intelligence";
    case "approval":
      return "#approvals";
    case "execute":
      return "/faculty/dashboard";
    case "audit":
      return "/faculty/audit";
    default:
      return null;
  }
};

export function FacultyCopilot() {
  const token = useAuthStore((s) => s.token);
  const [busyId, setBusyId] = useState<string | null>(null);

  const status = useQuery({ queryKey: ["fac-copilot"], queryFn: () => facultyApi.copilotStatus(token!), enabled: !!token });
  const interventions = useQuery({ queryKey: ["fac-interventions"], queryFn: () => facultyApi.interventions(token!), enabled: !!token });
  const audit = useQuery({ queryKey: ["fac-audit"], queryFn: () => facultyApi.auditLog(token!, 8, 0), enabled: !!token });

  const pending = interventions.data?.filter((i) => i.status === "pending") ?? [];

  const decide = async (id: string, decision: string) => {
    setBusyId(id);
    try {
      await facultyApi.decide(id, decision, token!);
      await interventions.refetch();
      await status.refetch();
      await audit.refetch();
    } finally {
      setBusyId(null);
    }
  };

  const stages = status.data?.stages ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Faculty Copilot" subtitle="Analysis → recommendation → approval → execute → audit" icon={Workflow} accent="bg-violet-100 text-violet-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
            <Workflow className="h-4 w-4" /> Pipeline
            <span className="ml-auto text-xs font-normal text-[var(--muted-foreground)]">{status.data?.staff_id}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-8">
            {stages.map((s, i) => {
              const meta = STAGE_ICONS[s.key] ?? { icon: Sparkles, accent: "bg-[var(--muted)] text-[var(--muted-foreground)]" };
              const Icon = meta.icon;
              const link = stageLink(s.key);
              const inner = (
                <div className="flex h-full flex-col items-center gap-1 rounded-xl border border-[var(--border)] p-3 text-center transition-colors hover:border-[var(--primary)]/40">
                  <span className={`grid h-9 w-9 place-items-center rounded-lg ${meta.accent}`}>
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="text-xl font-bold">{s.value}</span>
                  <span className="line-clamp-2 text-[11px] leading-tight text-[var(--muted-foreground)]">{s.label}</span>
                </div>
              );
              return (
                <div key={s.key} className="relative flex flex-col gap-2">
                  {i < stages.length - 1 && <ArrowRight className="absolute -right-3 top-5 z-10 hidden h-4 w-4 text-[var(--border)] lg:block" />}
                  {link ? <Link to={link}>{inner}</Link> : inner}
                </div>
              );
            })}
          </div>
          {!status.data && <p className="text-sm text-[var(--muted-foreground)]">Loading pipeline…</p>}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="card-shell" id="approvals">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <ShieldCheck className="h-4 w-4" /> Faculty Approval — pending ({pending.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {pending.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No pending approvals. Propose an intervention from a remedial plan or the dashboard.</p>}
            {pending.map((p) => (
              <div key={p.id} className="rounded-lg border border-[var(--border)] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-semibold">{p.student_id}</span>
                  <Badge tone="neutral">{p.course_code}</Badge>
                  <span className="ml-auto font-mono text-[11px] text-[var(--muted-foreground)]">{p.id.slice(0, 8)}</span>
                </div>
                <p className="mt-1 line-clamp-2 text-xs text-[var(--muted-foreground)]">{p.plan_text}</p>
                <div className="mt-2 flex items-center gap-2">
                  <Button size="sm" onClick={() => decide(p.id, "approve")} disabled={busyId === p.id}>Approve</Button>
                  <Button size="sm" variant="outline" onClick={() => decide(p.id, "reject")} disabled={busyId === p.id}>Reject</Button>
                  <span className="ml-auto text-[11px] text-[var(--muted-foreground)]">Approve executes the action and logs it</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <ScrollText className="h-4 w-4" /> Audit Log — latest ({audit.data?.total ?? 0})
              <Link to="/faculty/audit" className="ml-auto text-xs font-normal text-[var(--primary)]">View all →</Link>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1.5">
            {audit.data?.entries.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No audited actions yet.</p>}
            {audit.data?.entries.map((e) => (
              <div key={e.id} className="flex items-center gap-2 rounded-md border border-[var(--border)] px-3 py-1.5">
                <Badge tone="neutral" className="shrink-0 font-mono">{e.action}</Badge>
                <span className="line-clamp-1 min-w-0 flex-1 text-xs text-[var(--muted-foreground)]">
                  {typeof e.payload?.student_id === "string" ? e.payload.student_id : e.entity_type}
                  {typeof e.payload?.course_code === "string" ? ` · ${e.payload.course_code}` : ""}
                </span>
                <span className="shrink-0 text-[11px] text-[var(--muted-foreground)]">{new Date(e.created_at).toLocaleString()}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { to: "/faculty/intelligence", label: "Intelligence", icon: Sparkles, accent: "bg-amber-100 text-amber-600" },
          { to: "/faculty/tools", label: "Tools", icon: FlaskConical, accent: "bg-violet-100 text-violet-600" },
          { to: "/faculty/course-reports", label: "Course Reports", icon: Landmark, accent: "bg-emerald-100 text-emerald-600" },
          { to: "/faculty/dashboard", label: "My Dashboard", icon: GraduationCap, accent: "bg-sky-100 text-sky-600" },
        ].map(({ to, label, icon: Icon, accent }) => (
          <Link key={to} to={to} className="group flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-3 transition-all hover:-translate-y-0.5 hover:shadow-md">
            <span className={`grid h-9 w-9 place-items-center rounded-lg ${accent}`}><Icon className="h-4 w-4" /></span>
            <span className="text-sm font-medium">{label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
