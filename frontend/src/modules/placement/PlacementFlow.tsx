import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BarChart3, Briefcase, Building2, FileSearch, FileWarning, FileText, GraduationCap, ListChecks, Megaphone, Sparkles, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/core/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { placementApi } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

const STAGE_ICONS: Record<string, { icon: typeof Building2; accent: string }> = {
  company: { icon: Building2, accent: "bg-sky-100 text-sky-600" },
  jd_upload: { icon: FileText, accent: "bg-violet-100 text-violet-600" },
  jd_analyzer: { icon: FileSearch, accent: "bg-emerald-100 text-emerald-600" },
  eligibility: { icon: ListChecks, accent: "bg-teal-100 text-teal-600" },
  matching: { icon: Users, accent: "bg-amber-100 text-amber-600" },
  ranking: { icon: BarChart3, accent: "bg-orange-100 text-orange-600" },
  officer_review: { icon: Sparkles, accent: "bg-red-100 text-red-600" },
  notify: { icon: Megaphone, accent: "bg-pink-100 text-pink-600" },
  rounds: { icon: FileWarning, accent: "bg-indigo-100 text-indigo-600" },
  selection: { icon: GraduationCap, accent: "bg-green-100 text-green-600" },
  analytics: { icon: Briefcase, accent: "bg-slate-200 text-slate-700" },
};

const stageLink = (key: string) => {
  switch (key) {
    case "company":
      return "/placement/companies";
    case "jd_upload":
    case "jd_analyzer":
      return "/placement/jd";
    case "matching":
    case "ranking":
    case "eligibility":
      return "/placement/matching";
    case "officer_review":
    case "rounds":
    case "selection":
      return "/placement/drives";
    case "notify":
      return "/placement/notifications";
    case "analytics":
      return "/placement/analytics";
    default:
      return null;
  }
};

export function PlacementFlow() {
  const token = useAuthStore((s) => s.token);

  const status = useQuery({ queryKey: ["pl-flow"], queryFn: () => placementApi.flowStatus(token!), enabled: !!token });
  const companies = useQuery({ queryKey: ["pl-companies"], queryFn: () => placementApi.companies(token!), enabled: !!token });
  const jds = useQuery({ queryKey: ["pl-jds"], queryFn: () => placementApi.jds(token!), enabled: !!token });
  const drives = useQuery({ queryKey: ["pl-drives"], queryFn: () => placementApi.drives(token!), enabled: !!token });

  const stages = status.data?.stages ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Placement Officer Copilot" subtitle="Company → JD → Analyzer → Eligibility → Matching → Ranking → Review → Notify → Rounds → Selection → Analytics" icon={Briefcase} accent="bg-emerald-100 text-emerald-600" />

      {companies.data?.length === 0 && jds.data?.length === 0 && (
        <Card className="card-shell border-dashed">
          <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
            <Building2 className="h-10 w-10 text-[var(--muted-foreground)]" />
            <p className="text-sm text-[var(--muted-foreground)]">
              No companies or job descriptions yet. Add your first company, upload a JD, and the copilot will
              analyze it and drive matching → ranking → review → notify → rounds → selection.
            </p>
            <Link to="/placement/jd" className="rounded-md bg-[var(--primary)] px-4 py-2 text-sm font-medium text-white">
              Add first company + JD →
            </Link>
          </CardContent>
        </Card>
      )}

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
            <Briefcase className="h-4 w-4" /> Recruitment Pipeline
            <span className="ml-auto text-xs font-normal text-[var(--muted-foreground)]">{status.data?.total_students ?? "—"} students in cohort</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-11">
            {stages.map((s, i) => {
              const meta = STAGE_ICONS[s.key] ?? { icon: Briefcase, accent: "bg-[var(--muted)] text-[var(--muted-foreground)]" };
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
                  {i < stages.length - 1 && <ArrowRight className="absolute -right-2.5 top-5 z-10 hidden h-4 w-4 text-[var(--border)] xl:block" />}
                  {link ? <Link to={link}>{inner}</Link> : inner}
                </div>
              );
            })}
          </div>
          {!status.data && <p className="text-sm text-[var(--muted-foreground)]">Loading pipeline…</p>}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { to: "/placement/jd", label: "JD Analyzer", desc: "Upload JD → parsed skills, gates, CTC", icon: FileSearch, accent: "bg-emerald-100 text-emerald-600" },
          { to: "/placement/matching", label: "Job–Student Matching", desc: "Eligibility → match score → ranking", icon: Users, accent: "bg-amber-100 text-amber-600" },
          { to: "/placement/drives", label: "Drives & Rounds", desc: "Schedule drives, rounds, selections", icon: ListChecks, accent: "bg-indigo-100 text-indigo-600" },
          { to: "/placement/analytics", label: "Placement Analytics", desc: "Funnel, salary, skill demand, prediction", icon: BarChart3, accent: "bg-slate-200 text-slate-700" },
        ].map(({ to, label, desc, icon: Icon, accent }) => (
          <Link key={to} to={to} className="group flex flex-col gap-1 rounded-xl border border-[var(--border)] bg-[var(--card)] p-3 transition-all hover:-translate-y-0.5 hover:shadow-md">
            <span className={`grid h-9 w-9 place-items-center rounded-lg ${accent}`}><Icon className="h-4 w-4" /></span>
            <span className="text-sm font-medium">{label}</span>
            <span className="text-xs text-[var(--muted-foreground)]">{desc}</span>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { to: "/placement/companies", label: "Company CRM", desc: `${companies.data?.length ?? 0} companies` },
          { to: "/placement/gaps", label: "Employability Gaps + Training", desc: "Skills gaps and personalized plans" },
          { to: "/placement/notifications", label: "Notifications", desc: `${drives.data?.reduce((a, d) => a + d.notified, 0) ?? 0} students notified` },
          { to: "/placement/dashboard", label: "Command Center", desc: "Readiness, risk, shortlisting" },
          { to: "/placement/reports", label: "Automated Reports", desc: "One-click placement report" },
          { to: "/placement/analytics", label: "Prediction", desc: "Predicted placement rate" },
        ].map(({ to, label, desc }) => (
          <Link key={label} to={to} className="group flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-3 transition-all hover:-translate-y-0.5 hover:shadow-md">
            <ArrowRight className="h-4 w-4 text-[var(--muted-foreground)]" />
            <div className="min-w-0">
              <p className="text-sm font-medium">{label}</p>
              <p className="truncate text-xs text-[var(--muted-foreground)]">{desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
