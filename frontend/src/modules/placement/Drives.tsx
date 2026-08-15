import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ListChecks, UserCheck } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { placementApi, type DriveRow } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

const inputCls = "w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--primary)]";

export function Drives() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();

  const drives = useQuery({ queryKey: ["pl-drives"], queryFn: () => placementApi.drives(token!), enabled: !!token });
  const companies = useQuery({ queryKey: ["pl-companies"], queryFn: () => placementApi.companies(token!), enabled: !!token });
  const jds = useQuery({ queryKey: ["pl-jds"], queryFn: () => placementApi.jds(token!), enabled: !!token });
  const readiness = useQuery({ queryKey: ["placement-readiness"], queryFn: () => placementApi.readiness(token!, 1000), enabled: !!token });

  const [title, setTitle] = useState("");
  const [companyId, setCompanyId] = useState("");
  const [jdId, setJdId] = useState("");
  const [driveDate, setDriveDate] = useState("");
  const [mode, setMode] = useState("online");
  const [location, setLocation] = useState("");

  const [openDrive, setOpenDrive] = useState<string | null>(null);
  const [roundName, setRoundName] = useState("");
  const [roundDate, setRoundDate] = useState("");
  const [selDrive, setSelDrive] = useState("");
  const [selStudent, setSelStudent] = useState("");
  const [selRound, setSelRound] = useState("final");
  const [selCtc, setSelCtc] = useState("");

  const createDrive = useMutation({
    mutationFn: () =>
      placementApi.createDrive(
        { title, company_id: companyId, jd_id: jdId || null, drive_date: driveDate, mode, location },
        token!
      ),
    onSuccess: (row) => {
      setOpenDrive(row.id);
      setTitle(""); setDriveDate(""); setLocation("");
      qc.invalidateQueries({ queryKey: ["pl-drives"] });
    },
  });

  const addRound = useMutation({
    mutationFn: (d: DriveRow) =>
      placementApi.addRound(d.id, { name: roundName, round_order: (d.rounds?.length ?? 0) + 1, round_date: roundDate }, token!),
    onSuccess: () => {
      setRoundName(""); setRoundDate("");
      qc.invalidateQueries({ queryKey: ["pl-drives"] });
    },
  });

  const recordSel = useMutation({
    mutationFn: () =>
      placementApi.recordSelection(
        { drive_id: selDrive, student_id: selStudent, round_reached: selRound, offered_ctc: Number(selCtc) || 0, offer_status: "offered" },
        token!
      ),
    onSuccess: () => {
      setSelStudent(""); setSelRound("final"); setSelCtc("");
      qc.invalidateQueries({ queryKey: ["pl-drives"] });
    },
  });

  const pipelineFor = (d: DriveRow) => {
    const rows = d.rounds ?? [];
    return [
      { stage: "Notified", count: d.notified },
      ...rows.map((r) => ({ stage: r.name, count: 0 })),
      { stage: "Selected", count: (d.selections ?? []).length },
    ];
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Placement Drive Management" subtitle="Schedule drives, recruitment rounds, notify shortlisted students and record selections" icon={ListChecks} accent="bg-indigo-100 text-indigo-600" />

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm">Schedule a drive</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <div className="col-span-2 flex flex-col gap-1">
            <span className="text-xs text-[var(--muted-foreground)]">Drive title</span>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="TechCorp Drive 2026" />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-[var(--muted-foreground)]">Company</span>
            <select className={inputCls} value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
              <option value="">Pick…</option>
              {(companies.data ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-[var(--muted-foreground)]">JD</span>
            <select className={inputCls} value={jdId} onChange={(e) => setJdId(e.target.value)}>
              <option value="">None…</option>
              {(jds.data ?? []).map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-[var(--muted-foreground)]">Date</span>
            <Input type="date" value={driveDate} onChange={(e) => setDriveDate(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-[var(--muted-foreground)]">Mode</span>
            <select className={inputCls} value={mode} onChange={(e) => setMode(e.target.value)}>
              <option>online</option><option>onsite</option><option>hybrid</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-[var(--muted-foreground)]">Location</span>
            <Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Kigali" />
          </div>
          <div className="col-span-2 flex items-end">
            <Button onClick={() => createDrive.mutate()} disabled={!title || !companyId || !driveDate || createDrive.isPending}>
              {createDrive.isPending ? "Creating…" : "Schedule drive"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {(drives.data ?? []).map((d) => {
        const stages = pipelineFor(d);
        const max = Math.max(1, ...stages.map((s) => s.count));
        return (
          <Card key={d.id} className="card-shell">
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
                <ListChecks className="h-4 w-4" /> {d.title} · {d.company}
                <Badge tone={d.status === "completed" ? "success" : d.status === "scheduled" ? "neutral" : "warning"}>{d.status}</Badge>
                <span className="ml-auto text-xs font-normal text-[var(--muted-foreground)]">{d.drive_date} · {d.mode} · {d.notified} notified</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-end gap-3">
                {stages.map((s) => (
                  <div key={s.stage} className="flex min-w-16 flex-1 flex-col items-center gap-1">
                    <span className="text-sm font-bold">{s.count}</span>
                    <span className="h-2 w-full overflow-hidden rounded-full bg-[var(--muted)]">
                      <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${(s.count / max) * 100}%` }} />
                    </span>
                    <span className="truncate text-[11px] text-[var(--muted-foreground)]">{s.stage}</span>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                <div className="flex flex-col gap-2 rounded-lg border border-[var(--border)] p-3">
                  <p className="text-xs font-semibold text-[var(--muted-foreground)]">Rounds</p>
                  {(d.rounds ?? []).map((r) => (
                    <div key={r.id} className="flex items-center gap-2 text-sm">
                      <span className="font-medium">{r.round_order}. {r.name}</span>
                      <span className="text-xs text-[var(--muted-foreground)]">{r.round_date}</span>
                      <Badge tone="neutral" className="ml-auto">{r.status}</Badge>
                    </div>
                  ))}
                  {openDrive === d.id && (
                    <div className="flex flex-col gap-2 border-t border-[var(--border)] pt-2">
                      <Input placeholder="Round name (Aptitude, Technical…)" value={roundName} onChange={(e) => setRoundName(e.target.value)} />
                      <Input type="date" value={roundDate} onChange={(e) => setRoundDate(e.target.value)} />
                      <Button size="sm" variant="outline" disabled={!roundName || !roundDate || addRound.isPending} onClick={() => addRound.mutate(d)}>
                        Add round
                      </Button>
                    </div>
                  )}
                  <Button size="sm" variant="outline" onClick={() => setOpenDrive(openDrive === d.id ? null : d.id)}>
                    {openDrive === d.id ? "Close" : "Add round"}
                  </Button>
                </div>

                <div className="flex flex-col gap-2 rounded-lg border border-[var(--border)] p-3 lg:col-span-2">
                  <p className="text-xs font-semibold text-[var(--muted-foreground)]">Record selection (offer)</p>
                  <div className="flex flex-wrap items-end gap-2">
                    <div className="flex min-w-40 flex-1 flex-col gap-1">
                      <span className="text-[11px] text-[var(--muted-foreground)]">Student</span>
                      <select className={inputCls} value={selStudent} onChange={(e) => setSelStudent(e.target.value)}>
                        <option value="">Pick a shortlisted student…</option>
                        {(readiness.data ?? []).slice(0, 100).map((r) => (
                          <option key={r.student_id} value={r.student_id}>{r.student_id} · {r.band}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-[11px] text-[var(--muted-foreground)]">Round reached</span>
                      <Input value={selRound} onChange={(e) => setSelRound(e.target.value)} placeholder="final" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-[11px] text-[var(--muted-foreground)]">CTC (LPA)</span>
                      <Input value={selCtc} onChange={(e) => setSelCtc(e.target.value)} placeholder="15" />
                    </div>
                    <Button size="sm" disabled={!selStudent} onClick={() => { setSelDrive(d.id); recordSel.mutate(); }}>
                      <CheckCircle2 className="mr-1 h-4 w-4" /> Record
                    </Button>
                  </div>
                  {(d.selections ?? []).map((s) => (
                    <div key={s.id} className="flex items-center gap-2 text-sm">
                      <UserCheck className="h-4 w-4 text-green-600" />
                      <span className="font-mono font-medium">{s.student_id}</span>
                      <span className="text-xs text-[var(--muted-foreground)]">{s.round_reached}</span>
                      <Badge tone="success" className="ml-auto">{s.offer_status}{s.offered_ctc ? ` · ${s.offered_ctc} LPA` : ""}</Badge>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
      {drives.data?.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No drives yet — schedule one above.</p>}
    </div>
  );
}
