import { TestTube2 } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { facultyApi, type VivaQuestions as VivaResult } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";
import { CourseChips, ProviderBadge } from "./toolShared";

export function VivaQuestions() {
  const token = useAuthStore((s) => s.token);
  const [courseCode, setCourseCode] = useState("");
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(5);
  const [result, setResult] = useState<VivaResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    setError("");
    setLoading(true);
    try {
      setResult(await facultyApi.vivaQuestions({ course_code: courseCode, topic, count }, token!));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Viva Questions" subtitle="Understanding-focused viva voce question banks" icon={TestTube2} accent="bg-pink-100 text-pink-600" />

      <Card className="card-shell">
        <CardContent className="flex flex-col gap-3 pt-5">
          <CourseChips value={courseCode} onChange={setCourseCode} />
          <div className="flex flex-wrap items-center gap-2">
            <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic (optional)" className="h-10 w-56 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm outline-none focus:border-[var(--primary)]" />
            <input type="number" min={1} max={20} value={count} onChange={(e) => setCount(Number(e.target.value))} className="h-10 w-20 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm" />
            <Button type="button" onClick={run} disabled={loading}>{loading ? "Generating…" : "Generate questions"}</Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
              <TestTube2 className="h-4 w-4" /> {result.course_code || "General"} — {result.topic} <ProviderBadge provider={result.provider} />
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {result.questions.map((q) => (
              <div key={q.qno} className="rounded-lg border border-[var(--border)] p-3">
                <div className="flex items-start gap-2">
                  <span className="rounded-full bg-[var(--muted)] px-2 py-0.5 font-mono text-xs">{q.qno}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{q.question}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <Badge tone="neutral" className="capitalize">{q.focus}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-[var(--muted-foreground)]">Expected: {q.expected_points.join(" · ")}</p>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
