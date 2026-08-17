import { useQuery } from "@tanstack/react-query";
import { Handshake } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { EmptyState } from "@/core/components/ui/empty-state";
import { ErrorState } from "@/core/components/ui/error-state";
import { Skeleton } from "@/core/components/ui/skeleton";
import { Badge } from "@/core/components/ui/badge";
import { facultyApi } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";

const bandColor = (band: string) =>
  band === "ready" ? "success" : band === "needs_improvement" ? "warning" : "destructive";

export function FacultyPlacements() {
  const token = useAuthStore((s) => s.token);

  const overview = useQuery({
    queryKey: ["fac-placements"],
    queryFn: () => facultyApi.placementOverview(token!),
    enabled: !!token,
  });

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

              <Card className="card-shell">
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Student Readiness</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                          <th className="py-2 pr-4">Student</th>
                          <th className="py-2 pr-4">Score</th>
                          <th className="py-2 pr-4">Band</th>
                          <th className="py-2 pr-4">Placement Prob</th>
                          <th className="py-2 pr-4">Drivers</th>
                        </tr>
                      </thead>
                      <tbody>
                        {overview.data.students.map((s) => (
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
