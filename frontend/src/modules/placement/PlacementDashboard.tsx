import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { AlertTriangle, Briefcase, FileText, TrendingUp, Users } from "lucide-react";

import { StatCard } from "@/core/components/StatCard";
import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { placementApi, type PlacementReady, type ShortlistCandidate } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

function BandPill({ band }: { band: PlacementReady["band"] }) {
  const styles: Record<PlacementReady["band"], string> = {
    ready: "bg-green-600 text-white",
    needs_improvement: "bg-yellow-500 text-black",
    not_ready: "bg-red-600 text-white",
  };
  const labels: Record<PlacementReady["band"], string> = {
    ready: "Ready",
    needs_improvement: "Needs Improvement",
    not_ready: "Not Ready",
  };
  return <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${styles[band]}`}>{labels[band]}</span>;
}

export function PlacementDashboard() {
  const token = useAuthStore((s) => s.token);

  const overview = useQuery({
    queryKey: ["placement-overview"],
    queryFn: () => placementApi.overview(token!),
    enabled: !!token,
  });

  const readiness = useQuery({
    queryKey: ["placement-readiness"],
    queryFn: () => placementApi.readiness(token!, 100),
    enabled: !!token,
  });

  const atRisk = useQuery({
    queryKey: ["placement-at-risk"],
    queryFn: () => placementApi.atRisk(token!, 20),
    enabled: !!token,
  });

  const report = useQuery({
    queryKey: ["placement-report"],
    queryFn: () => placementApi.report(token!),
    enabled: !!token,
  });

  const [role, setRole] = useState("");
  const [minGpa, setMinGpa] = useState("6.5");
  const [skills, setSkills] = useState("");
  const [shortlist, setShortlist] = useState<{ role: string; eligible_count: number; candidates: ShortlistCandidate[] } | null>(null);
  const [shortlisting, setShortlisting] = useState(false);

  const runShortlist = async () => {
    if (!token) return;
    setShortlisting(true);
    try {
      const result = await placementApi.shortlist(
        {
          role,
          min_gpa: Number(minGpa),
          max_backlogs: 0,
          required_skills: skills.split(",").map((s) => s.trim()).filter(Boolean),
          limit: 25,
        },
        token
      );
      setShortlist(result);
    } finally {
      setShortlisting(false);
    }
  };

  const ov = overview.data;
  const maxDepartment = ov?.departments.length
    ? Math.max(...ov.departments.map((d) => d.avg_readiness))
    : 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Placement Command Center"
        subtitle="Readiness scoring, candidate shortlisting and placement intelligence"
        icon={Briefcase}
        accent="bg-emerald-100 text-emerald-600"
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Batch size" value={ov?.total_students} sub="scored students" icon={Users} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Predicted placement rate" value={ov?.predicted_placement_rate != null ? `${Math.round(ov.predicted_placement_rate * 100)}%` : "—"} sub="mean placement probability" icon={TrendingUp} accent="bg-emerald-100 text-emerald-600" />
        <StatCard label="Placement-ready" value={ov?.distribution.ready ?? "—"} sub="readiness ≥ 70" icon={Briefcase} accent="bg-violet-100 text-violet-600" />
        <StatCard label="Unplaced risk" value={ov?.funnel.at_risk ?? "—"} sub="placement prob < 40%" icon={AlertTriangle} accent="bg-red-100 text-red-600" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Placement readiness (top 25)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-1.5">
              {(readiness.data ?? []).slice(0, 25).map((r) => (
                <div key={r.student_id} className="flex items-center gap-2 border-b border-[var(--border)] pb-1.5 text-sm">
                  <span className="w-24 shrink-0 font-medium">{r.student_id}</span>
                  <span className="h-2 w-full max-w-xs overflow-hidden rounded-full bg-[var(--muted)]">
                    <span
                      className={`block h-full rounded-full ${
                        r.band === "ready" ? "bg-green-500" : r.band === "needs_improvement" ? "bg-yellow-500" : "bg-red-500"
                      }`}
                      style={{ width: `${r.readiness_score}%` }}
                    />
                  </span>
                  <span className="w-9 text-right">{r.readiness_score}</span>
                  <BandPill band={r.band} />
                  <span className="ml-auto hidden text-xs text-[var(--muted-foreground)] md:block">
                    model {Math.round(r.placement_probability * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Department comparison</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {(ov?.departments ?? []).map((d) => (
                <div key={d.program} className="flex items-center gap-2 text-sm">
                  <span className="w-32 shrink-0 truncate">{d.program}</span>
                  <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                    <span
                      className="block h-full rounded-full bg-[var(--primary)]"
                      style={{ width: `${maxDepartment ? (d.avg_readiness / maxDepartment) * 100 : 0}%` }}
                    />
                  </span>
                  <span className="w-10 text-right">{d.avg_readiness}</span>
                  <span className="w-12 text-right text-xs text-[var(--muted-foreground)]">{d.ready} ready</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-4 w-4" /> Batch report
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              <p>
                Placement rate:{" "}
                <strong>
                  {report.data?.predicted_placement_rate != null ? `${Math.round(report.data.predicted_placement_rate * 100)}%` : "—"}
                </strong>{" "}
                · Avg readiness <strong>{report.data?.avg_readiness ?? "—"}</strong>
              </p>
              <p className="mt-2 text-xs text-[var(--muted-foreground)]">{report.data?.note}</p>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>AI job–student shortlisting</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-sm text-[var(--muted-foreground)]">
              Enter a job spec; Beru gates on GPA and backlogs, then ranks candidates by match score.
              GPA is on the 4.0 scale.
            </p>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="flex flex-col gap-1">
                <span className="text-sm text-[var(--muted-foreground)]">Role</span>
                <Input value={role} onChange={(e) => setRole(e.target.value)} placeholder="Data Scientist" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-sm text-[var(--muted-foreground)]">Min GPA</span>
                <Input value={minGpa} onChange={(e) => setMinGpa(e.target.value)} placeholder="6.5" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-sm text-[var(--muted-foreground)]">Required skills (csv)</span>
                <Input value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="python, sql, ml" />
              </div>
            </div>
            <Button className="mt-3" onClick={runShortlist} disabled={shortlisting || !role}>
              {shortlisting ? "Scoring…" : "Shortlist candidates"}
            </Button>

            {shortlist && (
              <div className="mt-4">
                <p className="text-sm">
                  <strong>{shortlist.role}</strong>: {shortlist.eligible_count} eligible students.
                </p>
                <div className="mt-2 flex flex-col gap-1.5">
                  {shortlist.candidates.map((c) => (
                    <div key={c.student_id} className="flex items-center gap-2 border-b border-[var(--border)] pb-1.5 text-sm">
                      <span className="w-24 shrink-0 font-medium">{c.student_id}</span>
                      <span className="h-2 w-full max-w-xs overflow-hidden rounded-full bg-[var(--muted)]">
                        <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${c.match_score}%` }} />
                      </span>
                      <span className="w-12 text-right font-semibold">{c.match_score}%</span>
                      <span className="text-xs text-[var(--muted-foreground)]">GPA {c.gpa} · {c.backlogs} AR</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> Unplaced-student risk monitor
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {(atRisk.data ?? []).slice(0, 12).map((r) => (
              <div key={r.student_id} className="flex items-start gap-2 border-b border-[var(--border)] pb-2 text-sm">
                <span
                  className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
                    r.risk_level === "high" ? "bg-red-600 text-white" : "bg-yellow-500 text-black"
                  }`}
                >
                  {r.risk_level.toUpperCase()}
                </span>
                <div className="min-w-0">
                  <p className="font-medium">
                    {r.student_id} · {r.program}
                    <span className="ml-2 text-xs text-[var(--muted-foreground)]">GPA {r.gpa} · {Math.round(r.attendance_rate * 100)}% att</span>
                  </p>
                  <p className="text-xs text-[var(--muted-foreground)]">{r.reasons.join(" · ")}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
