import { FileText } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Select } from "@/core/components/ui/select";
import { facultyApi, type QuestionPaper as QuestionPaperResult } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";
import { ProviderBadge, CourseChips } from "./toolShared";

export function QuestionPaper() {
  const token = useAuthStore((s) => s.token);
  const [courseCode, setCourseCode] = useState("");
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [count, setCount] = useState(5);
  const [result, setResult] = useState<QuestionPaperResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    setError("");
    setLoading(true);
    try {
      setResult(await facultyApi.questionPaper({ course_code: courseCode, topic, difficulty, count }, token!));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Question Paper" subtitle="Generate balanced exam papers" icon={FileText} accent="bg-violet-100 text-violet-600" />

      <Card className="card-shell">
        <CardContent className="flex flex-col gap-3 pt-5">
          <CourseChips value={courseCode} onChange={setCourseCode} />
          <div className="flex flex-wrap items-center gap-2">
            <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic (optional)" className="h-10 w-56 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm outline-none focus:border-[var(--primary)]" />
            <Select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
              {["foundational", "intermediate", "advanced"].map((d) => <option key={d} value={d}>{d}</option>)}
            </Select>
            <input type="number" min={1} max={20} value={count} onChange={(e) => setCount(Number(e.target.value))} className="h-10 w-20 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm" />
            <Button type="button" onClick={run} disabled={loading}>{loading ? "Generating…" : "Generate paper"}</Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
              <FileText className="h-4 w-4" /> {result.course_code || "General"} — {result.topic}
              <ProviderBadge provider={result.provider} />
              <span className="ml-auto text-[var(--muted-foreground)]">Total {result.total_marks} marks · {result.difficulty}</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {result.questions.map((q) => (
              <div key={q.qno} className="rounded-lg border border-[var(--border)] p-3">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-[var(--muted)] px-2 py-0.5 font-mono text-xs">{q.qno}</span>
                  <span className="text-sm font-medium">{q.question}</span>
                  <Badge tone="neutral" className="ml-auto">{q.type} · {q.marks} marks</Badge>
                </div>
                <p className="mt-1 text-xs text-[var(--muted-foreground)]">Rubric: {q.rubric}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
