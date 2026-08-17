import { Code2 } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { facultyApi, type CodeReview as CodeReviewResult } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";
import { ProviderBadge } from "./toolShared";
import { ToolExportBar } from "@/core/components/ui/tool-export-bar";

const sevTone = (s: string) => (s === "high" ? "destructive" : s === "medium" ? "warning" : "neutral");

export function CodeReview() {
  const token = useAuthStore((s) => s.token);
  const [language, setLanguage] = useState("");
  const [code, setCode] = useState("");
  const [result, setResult] = useState<CodeReviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    if (!code.trim()) {
      setError("Paste code to review.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      setResult(await facultyApi.codeReview({ language, code }, token!));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Code Review" subtitle="Review student code for quality, correctness and safety" icon={Code2} accent="bg-red-100 text-red-600" />

      <Card className="card-shell">
        <CardContent className="flex flex-col gap-3 pt-5">
          <input value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="Language (e.g. Python)" className="h-10 w-56 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm outline-none focus:border-[var(--primary)]" />
          <textarea value={code} onChange={(e) => setCode(e.target.value)} placeholder="Paste the student's code…" rows={12} className="w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-1.5 font-mono text-sm outline-none focus:border-[var(--primary)]" />
          <div className="flex items-center gap-2">
            <Button type="button" onClick={run} disabled={loading}>{loading ? "Reviewing…" : "Review code"}</Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
              <Code2 className="h-4 w-4" /> {result.language || "Code"} <ProviderBadge provider={result.provider} />
              <Badge tone={result.score >= 75 ? "success" : result.score >= 50 ? "warning" : "destructive"} className="ml-auto">
                score {result.score}/100
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="text-sm">{result.summary}</p>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-600">Strengths</p>
              <ul className="list-inside list-disc text-sm text-[var(--muted-foreground)]">
                {result.strengths.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-red-600">Issues ({result.issues.length})</p>
              <div className="flex flex-col gap-1.5">
                {result.issues.map((i, idx) => (
                  <div key={idx} className="flex items-start gap-2 rounded-md border border-[var(--border)] px-3 py-1.5 text-sm">
                    <span className="font-mono text-xs text-[var(--muted-foreground)]">L{i.line}</span>
                    <span className="min-w-0 flex-1">{i.message}</span>
                    <Badge tone={sevTone(i.severity)}>{i.severity}</Badge>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Suggestions</p>
              <ul className="list-inside list-disc text-sm text-[var(--muted-foreground)]">
                {result.suggestions.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </div>
            <ToolExportBar data={result} label="Code Review" />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
