import { CopyX, ScanSearch } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { facultyApi } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";

const flagTone = (flag: string) => (flag === "high" ? "destructive" : flag === "medium" ? "warning" : "success");

export function Similarity() {
  const token = useAuthStore((s) => s.token);
  const [rows, setRows] = useState<{ student_id: string; text: string }[]>([
    { student_id: "", text: "" },
    { student_id: "", text: "" },
  ]);
  const [threshold, setThreshold] = useState(0.35);
  const [result, setResult] = useState<{ pairs: { student_a: string; student_b: string; similarity: number; flag: string }[]; note: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const updateRow = (i: number, key: "student_id" | "text", value: string) =>
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, [key]: value } : r)));

  const addRow = () => setRows((prev) => [...prev, { student_id: "", text: "" }]);
  const removeRow = (i: number) => setRows((prev) => prev.filter((_, idx) => idx !== i));

  const run = async () => {
    setError("");
    const clean = rows.filter((r) => r.student_id.trim() && r.text.trim());
    if (clean.length < 2) {
      setError("Add at least two submissions with text.");
      return;
    }
    setLoading(true);
    try {
      const res = await facultyApi.similarity(clean, threshold, token!);
      setResult({ pairs: res.pairs, note: res.note });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Similarity check failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Similarity Check" subtitle="N-gram plagiarism screen across student submissions" icon={CopyX} accent="bg-orange-100 text-orange-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm">Submissions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {rows.map((row, i) => (
            <div key={i} className="flex flex-col gap-2 rounded-lg border border-[var(--border)] p-3">
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-[var(--muted)] px-2 py-0.5 font-mono text-xs">#{i + 1}</span>
                <input
                  value={row.student_id}
                  onChange={(e) => updateRow(i, "student_id", e.target.value)}
                  placeholder="Student ID (e.g. BCS2301)"
                  className="h-8 w-44 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm outline-none focus:border-[var(--primary)]"
                />
                <button onClick={() => removeRow(i)} className="ml-auto text-xs text-[var(--muted-foreground)] hover:text-red-600" aria-label="Remove row">
                  Remove
                </button>
              </div>
              <textarea
                value={row.text}
                onChange={(e) => updateRow(i, "text", e.target.value)}
                placeholder="Paste the student's submission text…"
                rows={3}
                className="w-full rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-1.5 text-sm outline-none focus:border-[var(--primary)]"
              />
            </div>
          ))}

          <div className="flex flex-wrap items-center gap-4">
            <Button type="button" variant="outline" onClick={addRow}>+ Add submission</Button>
            <label className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
              Threshold
              <input
                type="number"
                step={0.05}
                min={0}
                max={1}
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                className="h-8 w-20 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm"
              />
            </label>
            <Button type="button" onClick={run} disabled={loading}>
              <ScanSearch className="mr-1 h-4 w-4" /> {loading ? "Checking…" : "Run check"}
            </Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><ScanSearch className="h-4 w-4" /> Results</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {result.pairs.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">{result.note}</p>
            ) : (
              result.pairs.map((p) => (
                <div key={`${p.student_a}-${p.student_b}`} className="flex items-center gap-3 rounded-lg border border-[var(--border)] px-3 py-2">
                  <span className="font-mono text-sm font-semibold">{p.student_a}</span>
                  <span className="text-[var(--muted-foreground)]">⇄</span>
                  <span className="font-mono text-sm font-semibold">{p.student_b}</span>
                  <div className="ml-auto flex items-center gap-2">
                    <span className="text-sm">{Math.round(p.similarity * 100)}% similar</span>
                    <Badge tone={flagTone(p.flag)}>{p.flag}</Badge>
                  </div>
                </div>
              ))
            )}
            <p className="rounded-lg border-l-4 border-[var(--primary)] bg-[var(--primary)]/5 px-3 py-2 text-sm">{result.note}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
