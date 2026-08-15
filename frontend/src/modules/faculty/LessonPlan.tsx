import { Presentation } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { facultyApi, type LessonPlan as LessonPlanResult } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";
import { CourseChips, ProviderBadge } from "./toolShared";

export function LessonPlan() {
  const token = useAuthStore((s) => s.token);
  const [courseCode, setCourseCode] = useState("");
  const [topic, setTopic] = useState("");
  const [minutes, setMinutes] = useState(50);
  const [result, setResult] = useState<LessonPlanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    if (!topic.trim()) {
      setError("Enter a topic.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      setResult(await facultyApi.lessonPlan({ course_code: courseCode, topic: topic.trim(), duration_minutes: minutes }, token!));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Lesson Plan" subtitle="Timed session structures with outcomes and assessment" icon={Presentation} accent="bg-sky-100 text-sky-600" />

      <Card className="card-shell">
        <CardContent className="flex flex-col gap-3 pt-5">
          <CourseChips value={courseCode} onChange={setCourseCode} />
          <div className="flex flex-wrap items-center gap-2">
            <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic (e.g. Database Normalisation)" className="h-10 w-64 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm outline-none focus:border-[var(--primary)]" />
            <input type="number" min={10} max={180} value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} className="h-10 w-24 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm" />
            <Button type="button" onClick={run} disabled={loading}>{loading ? "Generating…" : "Generate plan"}</Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
              <Presentation className="h-4 w-4" /> {result.topic} <ProviderBadge provider={result.provider} />
              <span className="ml-auto text-[var(--muted-foreground)]">{result.duration_minutes} min</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Learning outcomes</p>
              <ul className="list-inside list-disc text-sm text-[var(--muted-foreground)]">
                {result.learning_outcomes.map((o) => <li key={o}>{o}</li>)}
              </ul>
            </div>
            <div className="flex flex-col gap-2">
              {result.structure.map((s) => (
                <div key={s.phase} className="flex gap-3 rounded-lg border border-[var(--border)] p-3">
                  <span className="grid h-8 w-16 shrink-0 place-items-center rounded-md bg-[var(--muted)] text-xs font-semibold">{s.time_minutes}m</span>
                  <div>
                    <p className="text-sm font-medium">{s.phase}</p>
                    <p className="text-sm text-[var(--muted-foreground)]">{s.activity}</p>
                  </div>
                </div>
              ))}
            </div>
            <p className="rounded-lg border-l-4 border-[var(--primary)] bg-[var(--primary)]/5 px-3 py-2 text-sm">Assessment: {result.assessment}</p>
            <div className="flex flex-wrap gap-2">
              {result.materials.map((m) => (
                <span key={m} className="rounded-full border border-[var(--border)] px-2.5 py-0.5 text-xs">{m}</span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
