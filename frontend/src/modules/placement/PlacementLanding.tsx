import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BarChart3,
  Briefcase,
  Building2,
  FileSearch,
  FileSpreadsheet,
  FileText,
  ListChecks,
  Megaphone,
  Sparkles,
  Target,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/core/components/ui/badge";
import { placementApi } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

const TOOLS = [
  { to: "/placement/dashboard", label: "Command Center", blurb: "Readiness scoring, risk monitor and batch shortlisting.", icon: BarChart3, accent: "text-sky-600 bg-sky-100" },
  { to: "/placement/jd", label: "JD Analyzer", blurb: "Upload a JD → skills, eligibility gates, CTC and role type.", icon: FileSearch, accent: "text-emerald-600 bg-emerald-100" },
  { to: "/placement/matching", label: "Job–Student Matching", blurb: "Eligibility engine, AI candidate matching and ranking.", icon: Users, accent: "text-amber-600 bg-amber-100" },
  { to: "/placement/drives", label: "Drives & Rounds", blurb: "Schedule drives, recruitment rounds and selections.", icon: ListChecks, accent: "text-indigo-600 bg-indigo-100" },
  { to: "/placement/analytics", label: "Placement Analytics", blurb: "Funnel, salary, skill demand, departments and prediction.", icon: BarChart3, accent: "text-slate-600 bg-slate-100" },
  { to: "/placement/gaps", label: "Gaps & Training", blurb: "Employability gaps and personalized training plans.", icon: Target, accent: "text-teal-600 bg-teal-100" },
  { to: "/placement/companies", label: "Company CRM", blurb: "Partner companies, their drives and selections.", icon: Building2, accent: "text-cyan-600 bg-cyan-100" },
  { to: "/placement/import", label: "CSV Import", blurb: "Bulk import companies, JDs, drives and selections from CSV.", icon: FileSpreadsheet, accent: "text-orange-600 bg-orange-100" },
  { to: "/placement/notifications", label: "Notifications", blurb: "Students shortlisted and notified for drives.", icon: Megaphone, accent: "text-pink-600 bg-pink-100" },
  { to: "/placement/reports", label: "Automated Reports", blurb: "One-click cohort placement report.", icon: FileText, accent: "text-rose-600 bg-rose-100" },
] as const;

export function PlacementLanding() {
  const token = useAuthStore((s) => s.token);
  const username = useAuthStore((s) => s.username);

  const overview = useQuery({ queryKey: ["placement-overview"], queryFn: () => placementApi.overview(token!), enabled: !!token });
  const funnel = useQuery({ queryKey: ["pl-funnel"], queryFn: () => placementApi.funnel(token!), enabled: !!token });

  const stats = [
    { label: "Cohort", value: overview.data?.total_students ?? "…", sub: "students in batch", accent: "from-sky-500 to-cyan-500" },
    { label: "Predicted placement", value: overview.data?.predicted_placement_rate != null ? `${Math.round(overview.data.predicted_placement_rate * 100)}%` : "…", sub: "mean ML probability", accent: "from-emerald-500 to-teal-500" },
    { label: "Placement-ready", value: overview.data?.distribution.ready ?? "…", sub: "readiness ≥ 70", accent: "from-violet-500 to-fuchsia-500" },
    { label: "Offers", value: funnel.data?.offers ?? "…", sub: "recorded selections", accent: "from-amber-500 to-orange-500" },
  ];

  return (
    <div className="relative flex flex-col gap-8 overflow-hidden">
      <div className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -left-32 top-40 h-72 w-72 rounded-full bg-sky-500/10 blur-3xl" />

      <section className="fade-up relative rounded-3xl border border-[var(--border)] bg-gradient-to-br from-emerald-500/10 via-white/80 to-white p-8 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <Badge tone="primary">PLACEMENT COPILOT</Badge>
            <h1 className="mt-3 text-3xl font-extrabold tracking-tight lg:text-4xl">
              Welcome back, {username}
            </h1>
            <p className="mt-2 max-w-xl text-sm text-[var(--muted-foreground)]">
              Company → JD → eligibility → matching → rounds → selection → analytics — all in one place.
            </p>
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

      <section className="fade-up">
          <div className="mb-3 flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-[var(--primary)]" />
            <h2 className="text-lg font-bold tracking-tight">Everything a placement officer needs</h2>
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
          <div className="card-shell rounded-2xl border border-[var(--border)] bg-gradient-to-br from-emerald-500/10 to-transparent p-5">
            <h3 className="flex items-center gap-1.5 text-sm font-bold">
              <Sparkles className="h-4 w-4 text-[var(--primary)]" /> Quick actions
            </h3>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link to="/placement/jd" className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-medium transition-colors hover:bg-[var(--muted)]">
                Upload a job description →
              </Link>
              <Link to="/placement/matching" className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-medium transition-colors hover:bg-[var(--muted)]">
                Match + rank candidates →
              </Link>
              <Link to="/placement/drives" className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-medium transition-colors hover:bg-[var(--muted)]">
                Schedule a drive →
              </Link>
              <Link to="/placement/reports" className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-medium transition-colors hover:bg-[var(--muted)]">
                Generate the cohort report →
              </Link>
            </div>
          </div>
      </section>
    </div>
  );
}
