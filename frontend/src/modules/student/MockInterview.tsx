import { useState, type FormEvent } from "react";
import { RefreshCw, Send, Users } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { studentApi, type InterviewQuestion, type InterviewScore } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";

export function MockInterview() {
  const token = useAuthStore((s) => s.token);
  const [role, setRole] = useState("Machine Learning Engineer");
  const [question, setQuestion] = useState<InterviewQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [score, setScore] = useState<InterviewScore | null>(null);
  const [busy, setBusy] = useState<"" | "ask" | "score">("");
  const [error, setError] = useState("");

  const ask = async (e: FormEvent) => {
    e.preventDefault();
    if (!role.trim()) return;
    setBusy("ask");
    setScore(null);
    setAnswer("");
    setError("");
    try {
      setQuestion(await studentApi.mockInterview(token!, role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy("");
    }
  };

  const submitAnswer = async (e: FormEvent) => {
    e.preventDefault();
    if (!question || !answer.trim()) return;
    setBusy("score");
    setError("");
    try {
      setScore(await studentApi.mockInterviewScore(token!, { role, question: question.question, answer }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Mock Interview" subtitle="Role-specific questions with scored feedback" icon={Users} accent="bg-fuchsia-100 text-fuchsia-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Target role</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={ask} className="flex flex-wrap items-center gap-3">
            <input
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="e.g. Data Analyst"
              className="h-9 w-64 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 text-sm outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
            <Button type="submit" disabled={busy === "ask" || !role.trim()}>
              <RefreshCw className={`mr-1.5 h-4 w-4 ${busy === "ask" ? "animate-spin" : ""}`} /> New question
            </Button>
          </form>
        </CardContent>
      </Card>

      {question && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              Interview question
              <Badge tone={question.focus === "technical" ? "neutral" : "success"}>{question.focus}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="text-sm font-medium">{question.question}</p>
            {question.tip && <p className="text-xs text-[var(--muted-foreground)]">Tip: {question.tip}</p>}
            <form onSubmit={submitAnswer} className="flex flex-col gap-3">
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                rows={5}
                placeholder="Type your answer (use Situation-Task-Action-Result)…"
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <div className="flex justify-end">
                <Button type="submit" disabled={busy === "score" || !answer.trim()}>
                  <Send className="mr-1.5 h-4 w-4" /> {busy === "score" ? "Scoring…" : "Get feedback"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {score && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-3">
              <span className={`grid h-14 w-14 place-items-center rounded-xl text-xl font-bold ${score.score >= 70 ? "bg-emerald-100 text-emerald-700" : score.score >= 40 ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"}`}>
                {score.score}
              </span>
              <span>
                <span className="block text-sm font-semibold">Score / 100</span>
                <span className="block text-xs text-[var(--muted-foreground)]">provider: {score.provider}</span>
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-700">Strengths</p>
              <ul className="list-inside list-disc text-sm text-[var(--muted-foreground)]">
                {score.strengths.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </div>
            <div className="rounded-lg border border-red-200 bg-red-50 p-3">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-red-700">To improve</p>
              <ul className="list-inside list-disc text-sm text-[var(--muted-foreground)]">
                {score.weaknesses.map((w) => <li key={w}>{w}</li>)}
              </ul>
            </div>
            <p className="md:col-span-2 rounded-lg border border-[var(--border)] bg-[var(--muted)]/40 px-3 py-2 text-sm">
              <span className="font-semibold">Improvement tip:</span> {score.improvement_tip}
            </p>
          </CardContent>
        </Card>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
