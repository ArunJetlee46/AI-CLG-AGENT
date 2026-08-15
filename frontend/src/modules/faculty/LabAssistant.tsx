import { FlaskConical } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { facultyApi, type LabAssistant as LabResult } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";
import { ProviderBadge } from "./toolShared";

export function LabAssistant() {
  const token = useAuthStore((s) => s.token);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<LabResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    if (!question.trim()) {
      setError("Enter a lab question.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      setResult(await facultyApi.labAssistant({ question: question.trim() }, token!));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Lab Assistant" subtitle="Step-by-step, safety-aware lab guidance" icon={FlaskConical} accent="bg-orange-100 text-orange-600" />

      <Card className="card-shell">
        <CardContent className="flex flex-col gap-3 pt-5">
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="e.g. How do I neutralise a spill of dilute acid?" rows={3} className="w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-1.5 text-sm outline-none focus:border-[var(--primary)]" />
          <div className="flex items-center gap-2">
            <Button type="button" onClick={run} disabled={loading}>{loading ? "Thinking…" : "Get guidance"}</Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
              <FlaskConical className="h-4 w-4" /> Guidance <ProviderBadge provider={result.provider} />
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="text-sm">{result.answer}</p>
            <ol className="flex flex-col gap-1.5">
              {result.steps.map((s, i) => (
                <li key={s} className="flex gap-2 rounded-md border border-[var(--border)] px-3 py-1.5 text-sm">
                  <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-[var(--primary)]/10 text-xs font-bold text-[var(--primary)]">{i + 1}</span>
                  <span>{s}</span>
                </li>
              ))}
            </ol>
            <p className="rounded-lg border-l-4 border-red-500 bg-red-50 px-3 py-2 text-sm text-red-800">⚠ {result.safety_note}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
