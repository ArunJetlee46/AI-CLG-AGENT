import { ClipboardCheck } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { facultyApi, type AssignmentEval as AssignmentEvalResult } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";
import { CourseChips, ProviderBadge } from "./toolShared";
import { ToolExportBar } from "@/core/components/ui/tool-export-bar";

const gradeTone = (g: string) => (g === "A" || g === "B" ? "success" : g === "C" ? "warning" : "destructive");

export function AssignmentEval() {
  const token = useAuthStore((s) => s.token);
  const [courseCode, setCourseCode] = useState("");
  const [brief, setBrief] = useState("");
  const [rubric, setRubric] = useState("");
  const [submission, setSubmission] = useState("");
  const [result, setResult] = useState<AssignmentEvalResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    if (!submission.trim()) {
      setError("Paste a submission to evaluate.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      setResult(await facultyApi.assignmentEval({ course_code: courseCode, assignment_brief: brief, rubric, submission }, token!));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Assignment Evaluation" subtitle="Score submissions against your rubric" icon={ClipboardCheck} accent="bg-amber-100 text-amber-600" />

      <Card className="card-shell">
        <CardContent className="flex flex-col gap-3 pt-5">
          <CourseChips value={courseCode} onChange={setCourseCode} />
          <textarea value={brief} onChange={(e) => setBrief(e.target.value)} placeholder="Assignment brief (optional)" rows={2} className="w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-1.5 text-sm outline-none focus:border-[var(--primary)]" />
          <textarea value={rubric} onChange={(e) => setRubric(e.target.value)} placeholder="Rubric criteria, one per line (optional)" rows={2} className="w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-1.5 text-sm outline-none focus:border-[var(--primary)]" />
          <textarea value={submission} onChange={(e) => setSubmission(e.target.value)} placeholder="Paste the student's submission…" rows={6} className="w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-1.5 text-sm outline-none focus:border-[var(--primary)]" />
          <div className="flex items-center gap-2">
            <Button type="button" onClick={run} disabled={loading}>{loading ? "Evaluating…" : "Evaluate submission"}</Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
              <ClipboardCheck className="h-4 w-4" /> Result <ProviderBadge provider={result.provider} />
              <Badge tone={gradeTone(result.grade)} className="ml-auto">
                {result.grade} · {result.score}/{result.max_score} ({result.percentage}%)
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-col gap-2">
              {result.criteria.map((c) => (
                <div key={c.criterion} className="rounded-lg border border-[var(--border)] p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{c.criterion}</span>
                    <span className="text-sm text-[var(--muted-foreground)]">{c.score}/{c.max_marks}</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[var(--muted)]">
                    <div className="h-full bg-[var(--primary)]" style={{ width: `${Math.min(100, (c.score / c.max_marks) * 100)}%` }} />
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted-foreground)]">{c.comment}</p>
                </div>
              ))}
            </div>
            <p className="rounded-lg border-l-4 border-[var(--primary)] bg-[var(--primary)]/5 px-3 py-2 text-sm">{result.overall}</p>
            <ToolExportBar data={result} label="Assignment Evaluation" />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
