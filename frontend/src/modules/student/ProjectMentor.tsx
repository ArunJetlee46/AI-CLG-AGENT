import { useState, type FormEvent } from "react";
import { Rocket } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { studentApi, type ProjectMentor } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";

export function ProjectMentor() {
  const token = useAuthStore((s) => s.token);
  const [projectTitle, setProjectTitle] = useState("");
  const [description, setDescription] = useState("");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ProjectMentor | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    try {
      setResult(await studentApi.projectMentor(token!, { project_title: projectTitle, project_description: description, question }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Project Mentor" subtitle="Milestone coaching and blocker help for your project" icon={Rocket} accent="bg-orange-100 text-orange-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Your project</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="flex flex-col gap-3">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <input
                value={projectTitle}
                onChange={(e) => setProjectTitle(e.target.value)}
                placeholder="Project title (optional)"
                className="h-9 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 text-sm outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="What do you need help with? e.g. Where do I start?"
                className="h-9 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 text-sm outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
            </div>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={5}
              placeholder="Short description of the project (optional)…"
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
            <div className="flex justify-end">
              <Button type="submit" disabled={busy || !question.trim()}>
                {busy ? "Coaching…" : "Get mentor advice"}
              </Button>
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </form>
        </CardContent>
      </Card>

      {result && (
        <div className="flex flex-col gap-4">
          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                Milestone plan for {result.project_title}
                {result.provider && <Badge tone="neutral">{result.provider}</Badge>}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="flex flex-col gap-2">
                {result.milestones.map((m, i) => (
                  <li key={m} className="flex items-center gap-3 rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[var(--primary)]/10 text-xs font-bold text-[var(--primary)]">
                      {i + 1}
                    </span>
                    {m}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>

          <Card className="card-shell">
            <CardContent className="flex flex-col gap-3">
              <div className="rounded-lg border-l-4 border-orange-400 bg-orange-50 px-3 py-2 text-sm">
                <span className="font-semibold">Advice:</span> {result.advice}
              </div>
              <div className="rounded-lg border-l-4 border-emerald-500 bg-emerald-50 px-3 py-2 text-sm">
                <span className="font-semibold">Next action:</span> {result.next_action}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
