import { useQuery } from "@tanstack/react-query";
import { BarChart3, TrendingUp } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { placementApi } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

type Tab = "funnel" | "salary" | "skill" | "departments" | "prediction" | "coding" | "aptitude" | "communication";
const TABS: { key: Tab; label: string }[] = [
  { key: "funnel", label: "Funnel" },
  { key: "salary", label: "Salary" },
  { key: "skill", label: "Skill Demand" },
  { key: "departments", label: "Departments" },
  { key: "prediction", label: "Prediction" },
  { key: "coding", label: "Coding" },
  { key: "aptitude", label: "Aptitude" },
  { key: "communication", label: "Communication" },
];

function Bar({ label, value, max }: { label: string; value: number; max: number }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-40 shrink-0 truncate">{label}</span>
      <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
        <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${max ? (value / max) * 100 : 0}%` }} />
      </span>
      <span className="w-16 text-right font-semibold">{value}</span>
    </div>
  );
}

function FunnelView() {
  const token = useAuthStore((s) => s.token);
  const funnel = useQuery({ queryKey: ["pl-funnel"], queryFn: () => placementApi.funnel(token!), enabled: !!token });
  const f = funnel.data;
  if (!f) return <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>;
  const rows = [
    { label: "Cohort", value: f.cohort },
    { label: "Eligible", value: f.eligible },
    { label: "Shortlisted (notified)", value: f.shortlisted },
    { label: "Offers", value: f.offers },
    { label: "Joined", value: f.joined },
  ];
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-3">
        {[
          { label: "Eligible", value: `${f.conversion.eligible_pct}%` },
          { label: "Offer rate", value: `${f.conversion.offer_rate_pct}%` },
          { label: "Join rate", value: `${f.conversion.join_rate_pct}%` },
          { label: "Ready", value: f.ready },
          { label: "At risk", value: f.at_risk },
        ].map((s) => (
          <div key={s.label} className="flex-1 rounded-lg border border-[var(--border)] p-3 text-center">
            <p className="text-lg font-bold">{s.value}</p>
            <p className="text-[11px] text-[var(--muted-foreground)]">{s.label}</p>
          </div>
        ))}
      </div>
      {rows.map((r) => <Bar key={r.label} label={r.label} value={r.value} max={max} />)}
      <p className="text-xs text-[var(--muted-foreground)]">{f.note}</p>
    </div>
  );
}

function SalaryView() {
  const token = useAuthStore((s) => s.token);
  const salary = useQuery({ queryKey: ["pl-salary"], queryFn: () => placementApi.salary(token!), enabled: !!token });
  const s = salary.data;
  if (!s) return <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-3">
        {[
          { label: "Offers", value: s.overall.count },
          { label: "Avg CTC", value: s.overall.avg_ctc != null ? `${s.overall.avg_ctc} LPA` : "—" },
          { label: "Median CTC", value: s.overall.median_ctc != null ? `${s.overall.median_ctc} LPA` : "—" },
          { label: "Max CTC", value: s.overall.max_ctc != null ? `${s.overall.max_ctc} LPA` : "—" },
        ].map((x) => (
          <div key={x.label} className="flex-1 rounded-lg border border-[var(--border)] p-3 text-center">
            <p className="text-lg font-bold">{x.value}</p>
            <p className="text-[11px] text-[var(--muted-foreground)]">{x.label}</p>
          </div>
        ))}
      </div>
      <div>
        <p className="mb-1 text-xs font-semibold text-[var(--muted-foreground)]">By program</p>
        {Object.entries(s.by_program).map(([program, agg]) => (
          <div key={program} className="flex items-center gap-2 border-b border-[var(--border)] py-1 text-sm">
            <span className="w-40 truncate">{program}</span>
            <span>{agg.count} offers</span>
            <span className="ml-auto text-xs text-[var(--muted-foreground)]">avg {agg.avg_ctc ?? "—"} LPA · max {agg.max_ctc ?? "—"} LPA</span>
          </div>
        ))}
        {Object.keys(s.by_program).length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No selections recorded yet.</p>}
      </div>
      <div>
        <p className="mb-1 text-xs font-semibold text-[var(--muted-foreground)]">By sector</p>
        {Object.entries(s.by_sector).map(([sector, agg]) => (
          <div key={sector} className="flex items-center gap-2 border-b border-[var(--border)] py-1 text-sm">
            <span className="w-40 truncate">{sector}</span>
            <span>{agg.count} offers</span>
            <span className="ml-auto text-xs text-[var(--muted-foreground)]">avg {agg.avg_ctc ?? "—"} LPA · joined {agg.joined}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-[var(--muted-foreground)]">{s.note}</p>
    </div>
  );
}

function SkillView() {
  const token = useAuthStore((s) => s.token);
  const demand = useQuery({ queryKey: ["pl-demand"], queryFn: () => placementApi.skillDemand(token!), enabled: !!token });
  const d = demand.data;
  if (!d) return <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>;
  const max = Math.max(1, ...d.top_skills.map((s) => s.demand));
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm">Top in-demand skills across <strong>{d.total_jds}</strong> job description(s):</p>
      <div className="flex flex-col gap-2">
        {d.top_skills.slice(0, 15).map((s) => <Bar key={s.skill} label={s.skill} value={s.demand} max={max} />)}
        {d.top_skills.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No JDs uploaded yet — add companies and JDs to see skill demand.</p>}
      </div>
      <div>
        <p className="mb-1 text-xs font-semibold text-[var(--muted-foreground)]">By sector</p>
        {d.sectors.map((sector) => (
          <div key={sector.sector} className="rounded-lg border border-[var(--border)] p-2 text-sm">
            <p className="font-medium">{sector.sector} · {sector.jds} JD(s)</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {sector.top_skills.map((s) => (
                <span key={s.skill} className="rounded-full bg-[var(--muted)] px-2 py-0.5 text-xs">{s.skill} ({s.demand})</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DepartmentsView() {
  const token = useAuthStore((s) => s.token);
  const dept = useQuery({ queryKey: ["pl-dept"], queryFn: () => placementApi.departments(token!), enabled: !!token });
  const d = dept.data;
  if (!d) return <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>;
  const max = Math.max(1, ...d.programs.map((p) => p.avg_readiness));
  return (
    <div className="flex flex-col gap-2">
      {d.programs.map((p) => (
        <div key={p.program} className="flex items-center gap-2 text-sm">
          <span className="w-40 shrink-0 truncate">{p.program}</span>
          <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
            <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${(p.avg_readiness / max) * 100}%` }} />
          </span>
          <span className="w-10 text-right">{p.avg_readiness}</span>
          <span className="w-24 text-right text-xs text-[var(--muted-foreground)]">{p.ready}/{p.students} ready</span>
          <span className="w-24 text-right text-xs text-[var(--muted-foreground)]">avg CTC {p.avg_ctc ?? "—"} LPA</span>
        </div>
      ))}
    </div>
  );
}

function PredictionView() {
  const token = useAuthStore((s) => s.token);
  const pred = useQuery({ queryKey: ["pl-pred"], queryFn: () => placementApi.prediction(token!), enabled: !!token });
  const p = pred.data;
  if (!p) return <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-3">
        {[
          { label: "Predicted placement rate", value: p.predicted_placement_rate != null ? `${Math.round(p.predicted_placement_rate * 100)}%` : "—" },
          { label: "Cohort", value: p.cohort_size },
          { label: "Ready", value: p.ready_count },
          { label: "At risk", value: p.at_risk_count },
        ].map((x) => (
          <div key={x.label} className="flex-1 rounded-lg border border-[var(--border)] p-3 text-center">
            <p className="text-lg font-bold">{x.value}</p>
            <p className="text-[11px] text-[var(--muted-foreground)]">{x.label}</p>
          </div>
        ))}
      </div>
      <div>
        <p className="mb-1 text-xs font-semibold text-[var(--muted-foreground)]">By year</p>
        {p.trend.map((t) => <Bar key={t.year} label={`Year ${t.year}`} value={Math.round(t.predicted_rate * 100)} max={100} />)}
      </div>
      <p className="text-xs text-[var(--muted-foreground)]">{p.note}</p>
    </div>
  );
}

function AssessmentView({ kind }: { kind: "coding" | "aptitude" | "communication" }) {
  const token = useAuthStore((s) => s.token);
  const query = useQuery({
    queryKey: ["pl-assess", kind],
    queryFn: () => (kind === "coding" ? placementApi.codingAnalytics(token!) : kind === "aptitude" ? placementApi.aptitudeAnalytics(token!) : placementApi.communicationAnalytics(token!)),
    enabled: !!token,
  });
  const a = query.data;
  if (!a) return <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>;
  const max = Math.max(1, ...a.programs.map((p) => p.avg_score));
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-3">
        {[
          { label: "Overall avg", value: a.overall_avg },
          { label: "Overall pass rate", value: `${Math.round(a.overall_pass_rate * 100)}%` },
        ].map((x) => (
          <div key={x.label} className="flex-1 rounded-lg border border-[var(--border)] p-3 text-center">
            <p className="text-lg font-bold">{x.value}</p>
            <p className="text-[11px] text-[var(--muted-foreground)]">{x.label}</p>
          </div>
        ))}
      </div>
      {a.programs.map((p) => (
        <div key={p.program} className="flex items-center gap-2 text-sm">
          <span className="w-40 shrink-0 truncate">{p.program}</span>
          <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
            <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${(p.avg_score / max) * 100}%` }} />
          </span>
          <span className="w-10 text-right">{p.avg_score}</span>
          <span className="w-24 text-right text-xs text-[var(--muted-foreground)]">{Math.round(p.pass_rate * 100)}% pass</span>
        </div>
      ))}
      <p className="text-xs text-[var(--muted-foreground)]">{a.note}</p>
    </div>
  );
}

export function PlacementAnalytics() {
  const [tab, setTab] = useState<Tab>("funnel");
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Placement Analytics" subtitle="Funnel, salary, skill demand, departments, prediction and assessment analytics" icon={BarChart3} accent="bg-slate-200 text-slate-700" />
      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === t.key ? "bg-[var(--primary)] text-white" : "bg-[var(--muted)] text-[var(--muted-foreground)] hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <TrendingUp className="h-4 w-4" /> {TABS.find((t) => t.key === tab)?.label}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {tab === "funnel" && <FunnelView />}
          {tab === "salary" && <SalaryView />}
          {tab === "skill" && <SkillView />}
          {tab === "departments" && <DepartmentsView />}
          {tab === "prediction" && <PredictionView />}
          {tab === "coding" && <AssessmentView kind="coding" />}
          {tab === "aptitude" && <AssessmentView kind="aptitude" />}
          {tab === "communication" && <AssessmentView kind="communication" />}
        </CardContent>
      </Card>
    </div>
  );
}
