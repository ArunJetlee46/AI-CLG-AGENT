import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { TrendingUp, TrendingDown, Minus, Download } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { api } from "@/core/lib/api";
import { useAuthStore } from "@/core/stores/auth";

interface EffectivenessRecord {
  id: string;
  intervention_id: string;
  student_id: string;
  course_code: string;
  intervention_type: string;
  baseline_score: number;
  followup_score: number | null;
  improvement: number | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  notes: string;
}

interface EffectivenessSummary {
  total_interventions: number;
  completed: number;
  active: number;
  needs_review: number;
  avg_improvement: number;
  positive_outcomes: number;
  negative_outcomes: number;
  neutral_outcomes: number;
  success_rate: number;
  by_type: Record<string, { total: number; completed: number; avg_improvement: number }>;
}

const STATUS_BADGES: Record<string, "default" | "success" | "warning" | "destructive" | "neutral"> = {
  active: "default",
  completed: "success",
  needs_review: "warning",
  pending: "neutral",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString();
}

function formatScore(score: number | null): string {
  if (score === null) return "—";
  return `${score.toFixed(1)}`;
}

function formatImprovement(imp: number | null): string {
  if (imp === null) return "—";
  const sign = imp > 0 ? "+" : "";
  return `${sign}${imp.toFixed(1)}`;
}

export function InterventionEffectiveness() {
  const token = useAuthStore((s) => s.token);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");

  const summary = useQuery({
    queryKey: ["intervention-effectiveness-summary"],
    queryFn: () => api<EffectivenessSummary>("/interventions/effectiveness/summary", {}, token!),
    enabled: !!token,
  });

  const records = useQuery({
    queryKey: ["intervention-effectiveness", statusFilter, typeFilter, search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      if (typeFilter) params.set("type", typeFilter);
      if (search) params.set("search", search);
      params.set("limit", "100");
      return api<EffectivenessRecord[]>(`/interventions/effectiveness?${params}`, {}, token!);
    },
    enabled: !!token,
  });

  const types = ["tutoring", "attendance_check", "study_plan", "counseling", "retake", "other"];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Intervention Effectiveness"
        subtitle="Track the impact of student interventions over time"
        icon={TrendingUp}
        accent="bg-violet-100 text-violet-600"
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card className="card-shell">
          <CardContent className="flex flex-col gap-1 p-4">
            <p className="text-xs text-[var(--muted-foreground)] uppercase tracking-wide">Total Interventions</p>
            <p className="text-3xl font-bold">{summary.data?.total_interventions ?? "—"}</p>
          </CardContent>
        </Card>
        <Card className="card-shell">
          <CardContent className="flex flex-col gap-1 p-4">
            <p className="text-xs text-[var(--muted-foreground)] uppercase tracking-wide">Completed</p>
            <p className="text-3xl font-bold text-emerald-600">{summary.data?.completed ?? "—"}</p>
          </CardContent>
        </Card>
        <Card className="card-shell">
          <CardContent className="flex flex-col gap-1 p-4">
            <p className="text-xs text-[var(--muted-foreground)] uppercase tracking-wide">Active</p>
            <p className="text-3xl font-bold text-sky-600">{summary.data?.active ?? "—"}</p>
          </CardContent>
        </Card>
        <Card className="card-shell">
          <CardContent className="flex flex-col gap-1 p-4">
            <p className="text-xs text-[var(--muted-foreground)] uppercase tracking-wide">Avg Improvement</p>
            <p className="text-3xl font-bold">{summary.data?.avg_improvement ?? "—"}</p>
          </CardContent>
        </Card>
        <Card className="card-shell">
          <CardContent className="flex flex-col gap-1 p-4">
            <p className="text-xs text-[var(--muted-foreground)] uppercase tracking-wide">Success Rate</p>
            <p className="text-3xl font-bold text-emerald-600">{summary.data?.success_rate ?? "—"}%</p>
          </CardContent>
        </Card>
      </div>

      {/* Outcome Distribution */}
      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Outcome Distribution</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-4 p-0 pt-4">
          <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-lg">
            <TrendingUp className="h-6 w-6 text-emerald-600" />
            <div>
              <p className="text-xs text-[var(--muted-foreground)]">Positive</p>
              <p className="text-2xl font-bold text-emerald-600">{summary.data?.positive_outcomes ?? "—"}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-amber-50 rounded-lg">
            <Minus className="h-6 w-6 text-amber-600" />
            <div>
              <p className="text-xs text-[var(--muted-foreground)]">Neutral</p>
              <p className="text-2xl font-bold text-amber-600">{summary.data?.neutral_outcomes ?? "—"}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-red-50 rounded-lg">
            <TrendingDown className="h-6 w-6 text-red-600" />
            <div>
              <p className="text-xs text-[var(--muted-foreground)]">Negative</p>
              <p className="text-2xl font-bold text-red-600">{summary.data?.negative_outcomes ?? "—"}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* By Intervention Type */}
      {summary.data?.by_type && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Effectiveness by Type</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                    <th className="py-2 pr-4">Type</th>
                    <th className="py-2 pr-4">Total</th>
                    <th className="py-2 pr-4">Completed</th>
                    <th className="py-2 pr-4">Avg Improvement</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(summary.data.by_type).map(([type, stats]) => (
                    <tr key={type} className="border-b border-[var(--border)]">
                      <td className="py-2 pr-4 font-medium capitalize">{type.replace(/_/g, " ")}</td>
                      <td className="py-2 pr-4">{stats.total}</td>
                      <td className="py-2 pr-4">{stats.completed}</td>
                      <td className="py-2 pr-4">
                        <span className={stats.avg_improvement > 0 ? "text-emerald-600" : stats.avg_improvement < 0 ? "text-red-600" : ""}>
                          {stats.avg_improvement >= 0 ? "+" : ""}{stats.avg_improvement.toFixed(1)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Records Table */}
      <Card className="card-shell">
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <CardTitle className="text-sm font-semibold">Intervention Records</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              placeholder="Search student, course…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9 w-56 text-sm"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-9 w-40 text-sm rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="needs_review">Needs Review</option>
            </select>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="h-9 w-40 text-sm rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              <option value="">All types</option>
              {types.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </select>
            <Button variant="outline" size="sm">
              <Download className="mr-1.5 h-4 w-4" /> Export
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {records.isLoading && <p className="text-center text-[var(--muted-foreground)] py-8">Loading…</p>}
          {records.error && <p className="text-center text-red-600 py-8">Failed to load records</p>}
          {!records.isLoading && !records.error && records.data?.length === 0 && (
            <p className="text-center text-[var(--muted-foreground)] py-8">No intervention records found</p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                  <th className="py-2 pr-4">Student</th>
                  <th className="py-2 pr-4">Course</th>
                  <th className="py-2 pr-4">Type</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Baseline</th>
                  <th className="py-2 pr-4">Follow-up</th>
                  <th className="py-2 pr-4">Improvement</th>
                  <th className="py-2 pr-4">Started</th>
                  <th className="py-2 pr-4">Completed</th>
                  <th className="py-2 pr-4">Notes</th>
                </tr>
              </thead>
              <tbody>
                {records.data?.map((record) => (
                  <tr key={record.id} className="border-b border-[var(--border)]">
                    <td className="py-2 pr-4 font-mono text-xs">{record.student_id.slice(0, 8)}</td>
                    <td className="py-2 pr-4 font-medium">{record.course_code}</td>
                    <td className="py-2 pr-4 capitalize">{record.intervention_type.replace(/_/g, " ")}</td>
                    <td className="py-2 pr-4">
                      <Badge tone={STATUS_BADGES[record.status] ?? "neutral"}>
                        {record.status.replace(/_/g, " ")}
                      </Badge>
                    </td>
                    <td className="py-2 pr-4">{formatScore(record.baseline_score)}</td>
                    <td className="py-2 pr-4">{formatScore(record.followup_score)}</td>
                    <td className="py-2 pr-4">
                      <span className={record.improvement !== null && record.improvement > 0 ? "text-emerald-600 font-medium" : record.improvement !== null && record.improvement < 0 ? "text-red-600 font-medium" : ""}>
                        {formatImprovement(record.improvement)}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-xs">{formatDate(record.started_at)}</td>
                    <td className="py-2 pr-4 text-xs">{formatDate(record.completed_at)}</td>
                    <td className="py-2 pr-4 text-xs text-[var(--muted-foreground)] max-w-[200px] truncate">{record.notes || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}