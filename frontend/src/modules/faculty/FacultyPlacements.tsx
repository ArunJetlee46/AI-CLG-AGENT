import { useQuery } from "@tanstack/react-query";
import { Handshake, Search, ArrowUpDown } from "lucide-react";
import { useState, useMemo } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { EmptyState } from "@/core/components/ui/empty-state";
import { ErrorState } from "@/core/components/ui/error-state";
import { Skeleton } from "@/core/components/ui/skeleton";
import { Badge } from "@/core/components/ui/badge";
import { Input } from "@/core/components/ui/input";
import { facultyApi } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";
import { cn } from "@/core/lib/utils";

const BAND_TABS = [
  { key: "all", label: "All" },
  { key: "ready", label: "Ready" },
  { key: "needs_improvement", label: "Needs Improvement" },
  { key: "not_ready", label: "Not Ready" },
] as const;

type SortKey = "student_id" | "readiness_score" | "band" | "placement_probability";

const bandColor = (band: string) =>
  band === "ready" ? "success" : band === "needs_improvement" ? "warning" : "destructive";

const bandOrder = (band: string) => (band === "ready" ? 0 : band === "needs_improvement" ? 1 : 2);

export function FacultyPlacements() {
  const token = useAuthStore((s) => s.token);
  const [bandFilter, setBandFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("readiness_score");
  const [sortAsc, setSortAsc] = useState(false);

  const overview = useQuery({
    queryKey: ["fac-placements"],
    queryFn: () => facultyApi.placementOverview(token!),
    enabled: !!token,
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(key === "student_id"); }
  };

  const filtered = useMemo(() => {
    if (!overview.data) return [];
    let rows = overview.data.students;
    if (bandFilter !== "all") rows = rows.filter((s) => s.band === bandFilter);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter((s) => s.student_id.toLowerCase().includes(q) || s.drivers.some((d) => d.toLowerCase().includes(q)));
    }
    rows = [...rows].sort((a, b) => {
      if (sortKey === "band") return sortAsc ? bandOrder(a.band) - bandOrder(b.band) : bandOrder(b.band) - bandOrder(a.band);
      const av = a[sortKey] ?? -1;
      const bv = b[sortKey] ?? -1;
      if (typeof av === "string" && typeof bv === "string") return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return rows;
  }, [overview.data, bandFilter, search, sortKey, sortAsc]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Placement Overview"
        subtitle="Placement readiness of students across your courses"
        icon={Handshake}
        accent="bg-emerald-100 text-emerald-600"
      />

      {overview.isError && <ErrorState onRetry={() => overview.refetch()} />}

      {overview.isLoading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      )}

      {!overview.isLoading && !overview.isError && overview.data && (
        <div className="flex flex-col gap-6">
          {overview.data.students.length === 0 ? (
            <EmptyState
              title="No placement data"
              description="No enrolled students have placement readiness scores yet."
              icon={Handshake}
            />
          ) : (
            <>
              <Card className="card-shell">
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-3">
                    <Badge tone="neutral">{overview.data.summary.total} students</Badge>
                    <Badge tone="success">{overview.data.summary.ready} ready</Badge>
                    <Badge tone="warning">{overview.data.summary.needs_improvement} needs improvement</Badge>
                    <Badge tone="destructive">{overview.data.summary.not_ready} not ready</Badge>
                  </div>
                </CardContent>
              </Card>

              <div className="flex flex-wrap items-center gap-3">
                <div className="flex gap-1 rounded-lg border border-[var(--border)] bg-[var(--card)] p-1">
                  {BAND_TABS.map(({ key, label }) => (
                    <button
                      key={key}
                      onClick={() => setBandFilter(key)}
                      className={cn(
                        "rounded-md px-3 py-1 text-sm transition-colors",
                        bandFilter === key ? "bg-[var(--primary)]/10 font-medium text-[var(--primary)]" : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div className="relative flex-1 min-w-[200px]">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
                  <Input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search by student ID or driver..."
                    className="pl-9 text-sm"
                  />
                </div>
              </div>

              <Card className="card-shell">
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Student Readiness</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                          {([
                            { key: "student_id" as SortKey, label: "Student" },
                            { key: "readiness_score" as SortKey, label: "Score" },
                            { key: "band" as SortKey, label: "Band" },
                            { key: "placement_probability" as SortKey, label: "Placement Prob" },
                          ]).map(({ key, label }) => (
                            <th key={key} className="cursor-pointer select-none py-2 pr-4 hover:text-foreground" onClick={() => toggleSort(key)}>
                              <span className="inline-flex items-center gap-1">
                                {label}
                                <ArrowUpDown className={cn("h-3 w-3", sortKey === key ? "text-[var(--primary)]" : "opacity-40")} />
                              </span>
                            </th>
                          ))}
                          <th className="py-2 pr-4">Drivers</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.map((s) => (
                          <tr key={s.student_id} className="border-b border-[var(--border)]">
                            <td className="py-2 pr-4 font-mono font-medium">{s.student_id}</td>
                            <td className="py-2 pr-4">{s.readiness_score}/100</td>
                            <td className="py-2 pr-4">
                              <Badge tone={bandColor(s.band)}>
                                {s.band.replace(/_/g, " ").toUpperCase()}
                              </Badge>
                            </td>
                            <td className="py-2 pr-4">
                              {s.placement_probability != null
                                ? `${Math.round(s.placement_probability * 100)}%`
                                : "—"}
                            </td>
                            <td className="py-2 pr-4 text-xs text-[var(--muted-foreground)]">
                              {s.drivers.slice(0, 3).join(", ")}
                            </td>
                          </tr>
                        ))}
                        {filtered.length === 0 && (
                          <tr><td colSpan={5} className="py-4 text-center text-sm text-[var(--muted-foreground)]">No students match the current filters.</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  );
}
