import { useQuery } from "@tanstack/react-query";
import { GraduationCap, Target } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { placementApi } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

type Tab = "gaps" | "training";

export function GapAnalysis() {
  const token = useAuthStore((s) => s.token);
  const [tab, setTab] = useState<Tab>("gaps");

  const gaps = useQuery({ queryKey: ["pl-gaps"], queryFn: () => placementApi.gaps(token!), enabled: !!token });
  const training = useQuery({ queryKey: ["pl-training"], queryFn: () => placementApi.training(token!, 100), enabled: !!token });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Employability Gap Analysis & Training" subtitle="Student skills vs recruiter demand → gaps → personalized placement training plans" icon={Target} accent="bg-teal-100 text-teal-600" />

      <div className="flex gap-2">
        {(["gaps", "training"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === t ? "bg-[var(--primary)] text-white" : "bg-[var(--muted)] text-[var(--muted-foreground)]"
            }`}
          >
            {t === "gaps" ? `Skills gaps (${gaps.data?.students.length ?? 0})` : `Training plans (${training.data?.length ?? 0})`}
          </button>
        ))}
      </div>

      {tab === "gaps" && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="text-sm">Required skills (from live JDs)</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-1">
              {(gaps.data?.required_skills ?? []).map((s) => <Badge key={s} tone="primary">{s}</Badge>)}
            </div>
            {(gaps.data?.students ?? []).slice(0, 30).map((s) => (
              <div key={s.student_id} className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
                <span className="font-mono font-semibold">{s.student_id}</span>
                <span className="text-xs text-[var(--muted-foreground)]">{s.program}</span>
                <Badge tone={s.gap_count > 5 ? "destructive" : s.gap_count > 2 ? "warning" : "success"}>{s.gap_count} gaps</Badge>
                <div className="flex flex-wrap gap-1">
                  {s.gap_skills.slice(0, 6).map((g) => <Badge key={g}>{g}</Badge>)}
                </div>
                <span className="ml-auto hidden max-w-xs truncate text-xs text-[var(--muted-foreground)] md:block">{s.recommendation}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {tab === "training" && (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {(training.data ?? []).map((t) => (
            <Card key={t.student_id} className="card-shell">
              <CardContent className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <GraduationCap className="h-4 w-4 text-[var(--muted-foreground)]" />
                  <span className="font-mono font-semibold">{t.student_id}</span>
                  <span className="text-xs text-[var(--muted-foreground)]">{t.program}</span>
                  <span className="ml-auto text-xs text-[var(--muted-foreground)]">model {Math.round(t.placement_probability * 100)}%</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="h-2 w-24 overflow-hidden rounded-full bg-[var(--muted)]">
                    <span className="block h-full rounded-full bg-teal-500" style={{ width: `${t.readiness_score}%` }} />
                  </span>
                  <span className="text-[var(--muted-foreground)]">readiness {t.readiness_score}</span>
                  <Badge tone="neutral" className="ml-auto">weak: {t.weakest_component}</Badge>
                </div>
                {t.gap_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {t.gap_skills.slice(0, 6).map((g) => <Badge key={g}>{g}</Badge>)}
                  </div>
                )}
                <p className="text-sm">{t.plan}</p>
              </CardContent>
            </Card>
          ))}
          {training.data?.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No students need training — cohort is healthy.</p>}
        </div>
      )}
    </div>
  );
}
