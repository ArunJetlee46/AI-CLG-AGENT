import { Wrench } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Select } from "@/core/components/ui/select";
import { facultyApi, type TeachingMaterial as TeachingMaterialResult } from "@/modules/faculty/api";
import { useAuthStore } from "@/core/stores/auth";
import { CourseChips, ProviderBadge } from "./toolShared";
import { ToolExportBar } from "@/core/components/ui/tool-export-bar";

export function TeachingMaterial() {
  const token = useAuthStore((s) => s.token);
  const [courseCode, setCourseCode] = useState("");
  const [topic, setTopic] = useState("");
  const [format, setFormat] = useState("notes");
  const [result, setResult] = useState<TeachingMaterialResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    if (!topic.trim()) {
      setError("Enter a topic.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      setResult(await facultyApi.teachingMaterial({ course_code: courseCode, topic: topic.trim(), format }, token!));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Teaching Material" subtitle="Notes, slides or outlines for any topic" icon={Wrench} accent="bg-emerald-100 text-emerald-600" />

      <Card className="card-shell">
        <CardContent className="flex flex-col gap-3 pt-5">
          <CourseChips value={courseCode} onChange={setCourseCode} />
          <div className="flex flex-wrap items-center gap-2">
            <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic (e.g. Relational Algebra)" className="h-10 w-64 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 text-sm outline-none focus:border-[var(--primary)]" />
            <Select value={format} onChange={(e) => setFormat(e.target.value)}>
              {["notes", "slides", "outline"].map((f) => <option key={f} value={f}>{f}</option>)}
            </Select>
            <Button type="button" onClick={run} disabled={loading}>{loading ? "Generating…" : "Generate material"}</Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
              <Wrench className="h-4 w-4" /> {result.topic} <ProviderBadge provider={result.provider} />
              <Badge tone="neutral" className="ml-auto">{result.format}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="rounded-lg border-l-4 border-[var(--primary)] bg-[var(--primary)]/5 px-3 py-2 text-sm">{result.summary}</p>
            {result.outline.map((section) => (
              <div key={section.section} className="rounded-lg border border-[var(--border)] p-3">
                <p className="text-sm font-semibold">{section.section}</p>
                <ul className="mt-1 list-inside list-disc text-sm text-[var(--muted-foreground)]">
                  {section.points.map((p) => <li key={p}>{p}</li>)}
                </ul>
              </div>
            ))}
            <ToolExportBar data={result} label={result.topic || "Teaching Material"} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
