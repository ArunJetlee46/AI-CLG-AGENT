import { useState, type FormEvent } from "react";
import { ClipboardList } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { studentApi, type AssignmentAssist } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";

const KINDS = [
  { value: "plan", label: "Step-by-step plan" },
  { value: "hints", label: "Study hints" },
  { value: "rubric", label: "Marking rubric" },
] as const;

export function AssignmentAssistant() {
  const token = useAuthStore((s) => s.token);
  const [courseCode, setCourseCode] = useState("");
  const [assignmentText, setAssignmentText] = useState("");
  const [ask, setAsk] = useState<(typeof KINDS)[number]["value"]>("plan");
  const [result, setResult] = useState<AssignmentAssist | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!assignmentText.trim()) return;
    setBusy(true);
    setError("");
    try {
      setResult(await studentApi.assignmentAssist(token!, { course_code: courseCode, assignment_text: assignmentText, ask }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Assignment Assistant" subtitle="Get a plan, hints, or a rubric for any assignment" icon={ClipboardList} accent="bg-indigo-100 text-indigo-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Assignment brief</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="flex flex-col gap-3">
            <input
              value={courseCode}
              onChange={(e) => setCourseCode(e.target.value.toUpperCase())}
              placeholder="Course code (optional)"
              className="h-9 w-48 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 text-sm outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
            <textarea
              value={assignmentText}
              onChange={(e) => setAssignmentText(e.target.value)}
              rows={6}
              placeholder="Paste the assignment brief here…"
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
            <div className="flex flex-wrap items-center gap-2">
              {KINDS.map((k) => (
                <button
                  key={k.value}
                  type="button"
                  onClick={() => setAsk(k.value)}
                  className={`rounded-full border px-3 py-1 text-xs ${ask === k.value ? "border-[var(--primary)] bg-[var(--primary)]/10 font-medium text-[var(--primary)]" : "border-[var(--border)] text-[var(--muted-foreground)]"}`}
                >
                  {k.label}
                </button>
              ))}
              <Button type="submit" disabled={busy || !assignmentText.trim()} className="ml-auto">
                {busy ? "Working…" : "Get help"}
              </Button>
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              {result.summary}
              {result.provider && <Badge tone="neutral">{result.provider}</Badge>}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {result.points.map((p, i) => (
              <div key={i} className="rounded-lg border border-[var(--border)] p-3">
                <p className="text-sm font-semibold">
                  {i + 1}. {p.title}
                </p>
                <p className="mt-0.5 text-sm text-[var(--muted-foreground)]">{p.detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
