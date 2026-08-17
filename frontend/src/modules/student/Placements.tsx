import { useQuery } from "@tanstack/react-query";
import { Handshake } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { ErrorState } from "@/core/components/ui/error-state";
import { Skeleton } from "@/core/components/ui/skeleton";
import { Badge } from "@/core/components/ui/badge";
import { studentApi } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";


const bandColor = (band: string) =>
  band === "ready" ? "success" : band === "needs_improvement" ? "warning" : "destructive";

export function Placements() {
  const token = useAuthStore((s) => s.token);

  const placements = useQuery({
    queryKey: ["me-placements"],
    queryFn: () => studentApi.myPlacements(token!),
    enabled: !!token,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="My Placements"
        subtitle="Placement readiness, shortlists, and upcoming drives"
        icon={Handshake}
        accent="bg-emerald-100 text-emerald-600"
      />

      {placements.isError && <ErrorState onRetry={() => placements.refetch()} />}

      {placements.isLoading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      )}

      {!placements.isLoading && !placements.isError && placements.data && (
        <div className="flex flex-col gap-6">
          {/* Readiness */}
          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Placement Readiness</CardTitle>
            </CardHeader>
            <CardContent>
              {placements.data.readiness ? (
                <div className="flex flex-col gap-3">
                  <div className="flex items-end gap-3">
                    <span className="text-5xl font-bold">
                      {placements.data.readiness.readiness_score}
                    </span>
                    <span className="text-lg text-[var(--muted-foreground)]">/100</span>
                    <Badge tone={bandColor(placements.data.readiness.band)}>
                      {placements.data.readiness.band.replace(/_/g, " ").toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    {placements.data.readiness.components.map((c) => (
                      <div key={c.name} className="text-sm">
                        <div className="flex justify-between">
                          <span className="capitalize">{c.name}</span>
                          <span className="text-[var(--muted-foreground)]">
                            {Math.round(c.score * 100)}%
                          </span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-[var(--muted)]">
                          <div
                            className="h-full bg-[var(--primary)]"
                            style={{ width: `${Math.round(c.score * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {placements.data.readiness.placement_probability != null && (
                      <Badge tone="neutral">
                        Placement prob:{" "}
                        {Math.round(placements.data.readiness.placement_probability * 100)}%
                      </Badge>
                    )}
                  </div>
                  <ul className="list-inside list-disc text-xs text-[var(--muted-foreground)]">
                    {placements.data.readiness.drivers.map((d) => (
                      <li key={d}>{d}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">
                  Readiness data is not available yet. Enroll in courses to unlock it.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Shortlists */}
          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">
                Shortlist Notifications ({placements.data.shortlists.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {placements.data.shortlists.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">
                  No shortlist notifications yet.
                </p>
              ) : (
                <div className="flex flex-col gap-2">
                  {placements.data.shortlists.map((s) => (
                    <div
                      key={s.id}
                      className="rounded-lg border border-l-4 border-l-amber-400 border-[var(--border)] bg-amber-50/50 px-3 py-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{s.title}</span>
                        <span className="text-xs text-[var(--muted-foreground)]">
                          {s.created_at ? new Date(s.created_at).toLocaleDateString() : "—"}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">{s.body}</p>
                      {s.drive.company && (
                        <p className="mt-1 text-xs">
                          {s.drive.company}
                          {s.drive.drive_date ? ` · ${s.drive.drive_date}` : ""}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Upcoming drives */}
          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">
                Upcoming Drives ({placements.data.upcoming_drives.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {placements.data.upcoming_drives.length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">
                  No upcoming drives you have been notified for.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                        <th className="py-2 pr-4">Drive</th>
                        <th className="py-2 pr-4">Company</th>
                        <th className="py-2 pr-4">Date</th>
                        <th className="py-2 pr-4">Mode</th>
                        <th className="py-2 pr-4">Location</th>
                        <th className="py-2 pr-4">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {placements.data.upcoming_drives.map((d, i) => (
                        <tr key={i} className="border-b border-[var(--border)]">
                          <td className="py-2 pr-4 font-medium">{d.title ?? "—"}</td>
                          <td className="py-2 pr-4">{d.company ?? "—"}</td>
                          <td className="py-2 pr-4">{d.drive_date ?? "—"}</td>
                          <td className="py-2 pr-4 capitalize">{d.mode ?? "—"}</td>
                          <td className="py-2 pr-4">{d.location ?? "—"}</td>
                          <td className="py-2 pr-4">
                            <Badge
                              tone={
                                d.status === "scheduled"
                                  ? "neutral"
                                  : d.status === "completed"
                                    ? "success"
                                    : "warning"
                              }
                            >
                              {d.status ?? "—"}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          <p className="text-xs text-[var(--muted-foreground)]">
            {placements.data.note}
          </p>
        </div>
      )}
    </div>
  );
}
