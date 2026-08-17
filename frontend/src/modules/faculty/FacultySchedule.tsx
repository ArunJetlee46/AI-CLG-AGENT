import { useQuery } from "@tanstack/react-query";
import { CalendarClock } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { EmptyState } from "@/core/components/ui/empty-state";
import { ErrorState } from "@/core/components/ui/error-state";
import { Skeleton } from "@/core/components/ui/skeleton";
import { Badge } from "@/core/components/ui/badge";
import { facultyApi } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";

function DayCard({ day, slots }: { day: string; slots: { course_code: string; title: string; start: string; end: string; hours: number }[] }) {
  return (
    <Card className="card-shell">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">{day}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {slots.map((slot, i) => (
          <div
            key={i}
            className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/40 px-3 py-2"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-[var(--muted-foreground)]">
                {slot.start} – {slot.end}
              </span>
              <Badge tone="neutral" className="text-[10px]">
                {slot.hours}h
              </Badge>
            </div>
            <p className="mt-1 text-sm font-semibold">
              {slot.course_code}
              <span className="ml-1.5 font-normal text-[var(--muted-foreground)]">
                {slot.title}
              </span>
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function FacultySchedule() {
  const token = useAuthStore((s) => s.token);

  const schedule = useQuery({
    queryKey: ["fac-schedule"],
    queryFn: () => facultyApi.schedule(token!),
    enabled: !!token,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="My Schedule"
        subtitle="Weekly teaching timetable across your assigned courses"
        icon={CalendarClock}
        accent="bg-indigo-100 text-indigo-600"
      />

      {schedule.isError && <ErrorState onRetry={() => schedule.refetch()} />}

      {schedule.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
      )}

      {!schedule.isLoading && !schedule.isError && schedule.data && (
        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap gap-3">
            <Badge tone="neutral">{schedule.data.sessions} sessions</Badge>
            <Badge tone={schedule.data.overloaded ? "destructive" : "success"}>
              {schedule.data.total_hours}h / {schedule.data.max_hours}h
            </Badge>
            <Badge tone="neutral">{schedule.data.utilization}% utilised</Badge>
          </div>

          {schedule.data.days.length === 0 ? (
            <EmptyState
              title="No scheduled classes"
              description="Your teaching schedule will appear here once timetable entries are assigned."
              icon={CalendarClock}
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {schedule.data.days.map((d) => (
                <DayCard key={d.day} day={d.day} slots={d.slots} />
              ))}
            </div>
          )}

          <p className="text-xs text-[var(--muted-foreground)]">
            {schedule.data.advisory}
          </p>
        </div>
      )}
    </div>
  );
}
