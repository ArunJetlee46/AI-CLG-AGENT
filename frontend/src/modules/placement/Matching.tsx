import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Megaphone, Users } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { placementApi } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

export function Matching() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();

  const jds = useQuery({ queryKey: ["pl-jds"], queryFn: () => placementApi.jds(token!), enabled: !!token });
  const drives = useQuery({ queryKey: ["pl-drives"], queryFn: () => placementApi.drives(token!), enabled: !!token });

  const [jdId, setJdId] = useState("");
  const [driveId, setDriveId] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const matching = useQuery({
    queryKey: ["pl-match", jdId],
    queryFn: () => placementApi.matching(jdId, token!, 300),
    enabled: !!token && !!jdId,
  });

  const notify = useMutation({
    mutationFn: () => placementApi.notify(driveId, Array.from(selected), token!),
    onSuccess: () => {
      setSelected(new Set());
      qc.invalidateQueries({ queryKey: ["pl-drives"] });
    },
  });

  const toggle = (sid: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(sid)) next.delete(sid);
      else next.add(sid);
      return next;
    });
  };

  const m = matching.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="AI Job–Student Matching" subtitle="Eligibility gates → match score → candidate ranking → officer review → notify students" icon={Users} accent="bg-amber-100 text-amber-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm">Run matching</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row md:items-end">
          <div className="flex flex-1 flex-col gap-1">
            <span className="text-sm text-[var(--muted-foreground)]">Job description</span>
            <select
              className="w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--primary)]"
              value={jdId}
              onChange={(e) => setJdId(e.target.value)}
            >
              <option value="">Pick a JD…</option>
              {(jds.data ?? []).map((jd) => (
                <option key={jd.id} value={jd.id}>{jd.title} (GPA ≥ {jd.min_gpa}, ≤ {jd.max_backlogs} AR)</option>
              ))}
            </select>
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <span className="text-sm text-[var(--muted-foreground)]">Drive to notify for (optional)</span>
            <select
              className="w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--primary)]"
              value={driveId}
              onChange={(e) => setDriveId(e.target.value)}
            >
              <option value="">No drive (just match)…</option>
              {(drives.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>{d.title} · {d.company}</option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {m && (
        <>
          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
                <Users className="h-4 w-4" /> {m.title} — {m.eligible_count} eligible · {m.candidates.length} ranked
                <span className="ml-auto flex items-center gap-2">
                  <Badge tone="primary">{selected.size} selected</Badge>
                  <Button size="sm" disabled={!driveId || selected.size === 0 || notify.isPending} onClick={() => notify.mutate()}>
                    <Megaphone className="mr-1 h-4 w-4" /> Notify selected
                  </Button>
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-1.5">
              <div className="mb-1 flex flex-wrap gap-1">
                <span className="text-xs text-[var(--muted-foreground)]">Required skills:</span>
                {m.required_skills.slice(0, 15).map((s) => <Badge key={s}>{s}</Badge>)}
              </div>
              {m.candidates.map((c) => (
                <div
                  key={c.student_id}
                  className={`flex cursor-pointer flex-wrap items-center gap-2 rounded-lg border px-3 py-2 transition-colors ${
                    selected.has(c.student_id) ? "border-[var(--primary)] bg-[var(--primary)]/10" : "border-[var(--border)] hover:border-[var(--primary)]/40"
                  }`}
                  onClick={() => toggle(c.student_id)}
                >
                  <input type="checkbox" readOnly checked={selected.has(c.student_id)} className="h-4 w-4 accent-[var(--primary)]" />
                  <span className="font-mono text-sm font-semibold">{c.student_id}</span>
                  <span className="hidden text-xs text-[var(--muted-foreground)] md:block">{c.program}</span>
                  <span className="h-2 w-full max-w-[180px] overflow-hidden rounded-full bg-[var(--muted)]">
                    <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${c.match_score}%` }} />
                  </span>
                  <span className="w-12 text-right text-sm font-semibold">{c.match_score}%</span>
                  <span className="text-xs text-[var(--muted-foreground)]">GPA {c.gpa} · {c.backlogs} AR · model {Math.round(c.placement_probability * 100)}%</span>
                  <span className="ml-auto flex flex-wrap gap-1">
                    {c.skills_matched.slice(0, 4).map((s) => <Badge key={s}>{s}</Badge>)}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
          {notify.isSuccess && <p className="text-sm text-green-600">Notified {notify.data.notified} student(s) — visible in Notifications and the drive pipeline.</p>}
        </>
      )}
    </div>
  );
}
