import { useMutation } from "@tanstack/react-query";
import { Bot, Lightbulb, Send, Sparkles } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi, type CopilotResponse } from "@/modules/admin/api";

const intentStyles: Record<string, string> = {
  health: "bg-sky-100 text-sky-700",
  placement: "bg-emerald-100 text-emerald-700",
  dropout: "bg-red-100 text-red-700",
  departments: "bg-violet-100 text-violet-700",
  forecast: "bg-indigo-100 text-indigo-700",
  accreditation: "bg-amber-100 text-amber-700",
  resources: "bg-cyan-100 text-cyan-700",
  governance: "bg-fuchsia-100 text-fuchsia-700",
};

const SUGGESTIONS = [
  "How is the overall university health score?",
  "How is placement looking this year?",
  "How many students are at risk of dropout?",
  "What is the enrollment forecast for next year?",
];

export function AdminCopilot() {
  const token = useAuthStore((s) => s.token);
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<CopilotResponse[]>([]);

  const ask = useMutation({
    mutationFn: (q: string) => adminApi.copilot(q, token!),
    onSuccess: (result) => {
      setHistory((h) => [result, ...h]);
      setQuestion("");
    },
  });

  const submit = (q: string) => {
    if (!q.trim() || ask.isPending) return;
    ask.mutate(q.trim());
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="AI Admin Copilot" subtitle="Ask questions about the university — grounded in live institution data" icon={Sparkles} />

      <Card>
        <CardContent className="pt-5">
          <div className="flex gap-2">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit(question)}
              placeholder="Ask anything: health, placement, dropout risk, departments, forecast…"
            />
            <Button disabled={!question.trim() || ask.isPending} onClick={() => submit(question)}>
              <Send className="h-4 w-4" /> Ask
            </Button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <Button key={s} size="sm" variant="outline" disabled={ask.isPending} onClick={() => submit(s)}>
                {s}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {ask.isPending && <p className="text-sm text-[var(--muted-foreground)]">Analyzing institution data…</p>}

      <div className="flex flex-col gap-4">
        {history.map((r, i) => (
          <Card key={i}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-4 w-4" /> {r.question}
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${intentStyles[r.intent] ?? "bg-[var(--muted)]"}`}>
                  {r.intent}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <p className="text-sm leading-relaxed">{r.summary}</p>

              {r.key_numbers.length > 0 && (
                <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                  {r.key_numbers.map((n) => (
                    <div key={n.label} className="rounded-lg bg-[var(--muted)] px-3 py-2">
                      <p className="text-xs text-[var(--muted-foreground)]">{n.label}</p>
                      <p className="text-lg font-bold">{n.value}</p>
                    </div>
                  ))}
                </div>
              )}

              {r.suggested_actions.length > 0 && (
                <div>
                  <p className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                    <Lightbulb className="h-3.5 w-3.5" /> Suggested actions
                  </p>
                  <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
                    {r.suggested_actions.map((a, j) => (
                      <li key={j}>{a}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted-foreground)]">
                <span className="rounded-full bg-[var(--primary)]/10 px-2 py-0.5 font-mono">{r.provider}</span>
                <span>based on: {r.citations.join(", ") || "live analytics"}</span>
              </div>
            </CardContent>
          </Card>
        ))}
        {history.length === 0 && !ask.isPending && (
          <p className="text-sm text-[var(--muted-foreground)]">
            No questions yet. Try one of the suggestions above.
          </p>
        )}
      </div>
    </div>
  );
}
