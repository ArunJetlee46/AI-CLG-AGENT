import { useQuery } from "@tanstack/react-query";
import { CalendarClock } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { EmptyState } from "@/core/components/ui/empty-state";
import { ErrorState } from "@/core/components/ui/error-state";
import { Skeleton } from "@/core/components/ui/skeleton";
import { Badge } from "@/core/components/ui/badge";
import { studentApi, type TimetableEntry } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";

function DayCard({ day, entries }: { day: string; entries: TimetableEntry[] }) {
  return (
    <Card className="card-shell">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">{day}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {entries.map((entry, i) => (
          <div
            key={i}
            className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/40 px-3 py-2"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-[var(--muted-foreground)]">
                {entry.start_time} – {entry.end_time}
              </span>
              <Badge tone="neutral" className="font-mono text-[10px]">
                {entry.room}
              </Badge>
            </div>
            <p className="mt-1 text-sm font-semibold">
              {entry.course_code}
              <span className="ml-1.5 font-normal text-[var(--muted-foreground)]">
                {entry.course_title}
              </span>
            </p>
            <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">
              {entry.lecturer} · {entry.credits} cr
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function Schedule() {
  const token = useAuthStore((s) => s.token);

  const timetable = useQuery({
    queryKey: ["me-timetable"],
    queryFn: () => studentApi.myTimetable(token!),
    enabled: !!token,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="My Schedule"
        subtitle="Weekly timetable from your enrolled courses"
        icon={CalendarClock}
        accent="bg-indigo-100 text-indigo-600"
      />

      {timetable.isError && <ErrorState onRetry={() => timetable.refetch()} />}

      {timetable.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
      )}

      {!timetable.isLoading && !timetable.isError && timetable.data && (
        <>
          {timetable.data.days.length === 0 ? (
            <EmptyState
              title="No scheduled classes"
              description="Enroll in courses and wait for the timetable to be published."
              icon={CalendarClock}
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {timetable.data.days.map((day) => (
                <DayCard key={day} day={day} entries={timetable.data!.by_day[day] ?? []} />
              ))}
            </div>
          )}
          <p className="text-xs text-[var(--muted-foreground)]">
            {timetable.data.entries.length} session(s) across {timetable.data.days.length} day(s).
          </p>
        </>
      )}
    </div>
  );
}
