import { useState, type FormEvent } from "react";
import { FileText } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { studentApi, type ResumeATS } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";

export function ResumeATS() {
  const token = useAuthStore((s) => s.token);
  const [resumeText, setResumeText] = useState("");
  const [result, setResult] = useState<ResumeATS | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (resumeText.trim().length < 20) return;
    setBusy(true);
    setError("");
    try {
      setResult(await studentApi.resumeAts(token!, resumeText));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Resume / ATS Check" subtitle="Score your resume against ATS parsing rules" icon={FileText} accent="bg-rose-100 text-rose-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Resume text</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="flex flex-col gap-3">
            <textarea
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              rows={9}
              placeholder="Paste the plain-text version of your resume (at least 20 characters)…"
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
            <div className="flex justify-end">
              <Button type="submit" disabled={busy || resumeText.trim().length < 20}>
                {busy ? "Scoring…" : "Run ATS check"}
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
              <CardTitle className="flex items-center gap-3">
                <span className={`grid h-16 w-16 place-items-center rounded-xl text-2xl font-bold ${result.score >= 70 ? "bg-emerald-100 text-emerald-700" : result.score >= 40 ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"}`}>
                  {result.score}
                </span>
                <span>
                  <span className="block text-sm font-semibold">ATS score / 100</span>
                  <span className="block text-xs text-[var(--muted-foreground)]">provider: {result.provider}</span>
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-2">
                {Object.entries(result.section_scores).map(([key, value]) => (
                  <div key={key} className="text-sm">
                    <div className="flex justify-between">
                      <span className="capitalize">{key}</span>
                      <span className="text-[var(--muted-foreground)]">{value}/100</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-[var(--muted)]">
                      <div className="h-full bg-[var(--primary)]" style={{ width: `${value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              {result.matched_skills.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {result.matched_skills.map((s) => (
                    <Badge key={s} tone="success">{s}</Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Improvements</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="flex flex-col gap-2">
                {result.suggestions.map((s) => (
                  <li key={s} className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
                    {s}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
