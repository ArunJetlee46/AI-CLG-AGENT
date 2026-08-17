import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useRef } from "react";
import { Handshake, FileUp, CheckCircle2, XCircle, Upload, X } from "lucide-react";

import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { ErrorState } from "@/core/components/ui/error-state";
import { Skeleton } from "@/core/components/ui/skeleton";
import { Badge } from "@/core/components/ui/badge";
import { toast } from "@/core/components/ui/toast";
import { studentApi } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";


const bandColor = (band: string) =>
  band === "ready" ? "success" : band === "needs_improvement" ? "warning" : "destructive";

const offerStatusTone = (s: string) =>
  s === "offered" ? "warning" : s === "accepted" ? "success" : s === "joined" ? "success" : "destructive";

export function Placements() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const placements = useQuery({
    queryKey: ["me-placements"],
    queryFn: () => studentApi.myPlacements(token!),
    enabled: !!token,
  });

  const applyMut = useMutation({
    mutationFn: (driveId: string) => studentApi.applyToDrive(driveId, token!),
    onSuccess: () => { toast.success("Applied", "Your application has been submitted."); qc.invalidateQueries({ queryKey: ["me-placements"] }); },
    onError: (err: Error) => toast.error("Application failed", err.message),
  });

  const withdrawMut = useMutation({
    mutationFn: (driveId: string) => studentApi.withdrawApplication(driveId, token!),
    onSuccess: () => { toast.success("Withdrawn", "Your application has been withdrawn."); qc.invalidateQueries({ queryKey: ["me-placements"] }); },
    onError: (err: Error) => toast.error("Withdraw failed", err.message),
  });

  const decideMut = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "accepted" | "rejected" }) =>
      studentApi.decideOffer(id, decision, token!),
    onSuccess: () => { toast.success("Decision recorded", "Your response has been saved."); qc.invalidateQueries({ queryKey: ["me-placements"] }); },
    onError: (err: Error) => toast.error("Decision failed", err.message),
  });

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;
    setUploading(true);
    try {
      await studentApi.uploadResume(file, token);
      toast.success("Resume uploaded", "Your resume has been parsed and skills extracted.");
      qc.invalidateQueries({ queryKey: ["me-placements"] });
    } catch (err) {
      toast.error("Upload failed", err instanceof Error ? err.message : "Could not upload resume");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const deleteResumeMut = useMutation({
    mutationFn: () => studentApi.deleteResume(token!),
    onSuccess: () => { toast.success("Resume deleted"); qc.invalidateQueries({ queryKey: ["me-placements"] }); },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-100 text-emerald-600">
            <Handshake className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold">My Placements</h1>
            <p className="text-sm text-[var(--muted-foreground)]">Readiness, drives, applications, offers, and resume</p>
          </div>
        </div>
      </div>

      {placements.isError && <ErrorState onRetry={() => placements.refetch()} />}

      {placements.isLoading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-48 rounded-xl" />)}
        </div>
      )}

      {!placements.isLoading && !placements.isError && placements.data && (
        <div className="flex flex-col gap-6">
          {/* Readiness */}
          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Placement Readiness</CardTitle>
            </CardHeader>
            <CardContent>
              {placements.data.readiness ? (
                <div className="flex flex-col gap-3">
                  <div className="flex items-end gap-3">
                    <span className="text-5xl font-bold">{placements.data.readiness.readiness_score}</span>
                    <span className="text-lg text-[var(--muted-foreground)]">/100</span>
                    <Badge tone={bandColor(placements.data.readiness.band)}>
                      {placements.data.readiness.band.replace(/_/g, " ").toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    {placements.data.readiness.components.map((c) => (
                      <div key={c.name} className="text-sm">
                        <div className="flex justify-between">
                          <span className="capitalize">{c.name}</span>
                          <span className="text-[var(--muted-foreground)]">{Math.round(c.score * 100)}%</span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-[var(--muted)]">
                          <div className="h-full bg-[var(--primary)]" style={{ width: `${Math.round(c.score * 100)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {placements.data.readiness.placement_probability != null && (
                      <Badge tone="neutral">Placement prob: {Math.round(placements.data.readiness.placement_probability * 100)}%</Badge>
                    )}
                  </div>
                  <ul className="list-inside list-disc text-xs text-[var(--muted-foreground)]">
                    {placements.data.readiness.drivers.map((d) => <li key={d}>{d}</li>)}
                  </ul>
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">Readiness data is not available yet. Enroll in courses to unlock it.</p>
              )}
            </CardContent>
          </Card>

          {/* Resume */}
          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <FileUp className="h-4 w-4" /> Resume
              </CardTitle>
            </CardHeader>
            <CardContent>
              {placements.data.resume ? (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--muted)]/40 px-3 py-2">
                    <div>
                      <p className="text-sm font-medium">{placements.data.resume.filename}</p>
                      <p className="text-xs text-[var(--muted-foreground)]">
                        Uploaded {placements.data.resume.uploaded_at ? new Date(placements.data.resume.uploaded_at).toLocaleDateString() : "—"}
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => deleteResumeMut.mutate()} disabled={deleteResumeMut.isPending}>
                      <X className="h-3 w-3 mr-1" /> Remove
                    </Button>
                  </div>
                  {placements.data.resume.skills.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-[var(--muted-foreground)] mb-1">Extracted Skills</p>
                      <div className="flex flex-wrap gap-1">
                        {placements.data.resume.skills.map((s) => (
                          <Badge key={s} tone="neutral" className="capitalize text-xs">{s.replace(/_/g, " ")}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3 rounded-lg border-2 border-dashed border-[var(--border)] px-6 py-8">
                  <Upload className="h-8 w-8 text-[var(--muted-foreground)]" />
                  <p className="text-sm text-[var(--muted-foreground)]">Upload your resume to improve placement matching</p>
                  <p className="text-xs text-[var(--muted-foreground)]">PDF, DOCX, or TXT (max 5MB)</p>
                  <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
                    {uploading ? "Uploading..." : "Choose file"}
                  </Button>
                </div>
              )}
              <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.txt" className="hidden" onChange={handleUpload} />
            </CardContent>
          </Card>

          {/* Open Drives */}
          {placements.data.open_drives.length > 0 && (
            <Card className="card-shell">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">
                  Available Drives ({placements.data.open_drives.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                        <th className="py-2 pr-4">Company</th>
                        <th className="py-2 pr-4">Role</th>
                        <th className="py-2 pr-4">Date</th>
                        <th className="py-2 pr-4">Mode</th>
                        <th className="py-2 pr-4">Status</th>
                        <th className="py-2 pr-4">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {placements.data.open_drives.map((d) => (
                        <tr key={d.id} className="border-b border-[var(--border)]">
                          <td className="py-2 pr-4 font-medium">{d.company ?? "—"}</td>
                          <td className="py-2 pr-4">{d.title ?? "—"}</td>
                          <td className="py-2 pr-4">{d.drive_date ?? "—"}</td>
                          <td className="py-2 pr-4 capitalize">{d.mode ?? "—"}</td>
                          <td className="py-2 pr-4">
                            <Badge tone="neutral">{d.status}</Badge>
                          </td>
                          <td className="py-2 pr-4">
                            {d.applied ? (
                              <Button variant="outline" size="sm" onClick={() => withdrawMut.mutate(d.id!)} disabled={withdrawMut.isPending}>
                                Withdraw
                              </Button>
                            ) : (
                              <Button size="sm" onClick={() => applyMut.mutate(d.id!)} disabled={applyMut.isPending}>
                                Apply
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* My Applications */}
          {placements.data.applications.length > 0 && (
            <Card className="card-shell">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">
                  My Applications ({placements.data.applications.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col gap-2">
                  {placements.data.applications.map((a) => (
                    <div key={a.id} className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2">
                      <div>
                        <span className="text-sm font-medium">{a.drive.company ?? "Unknown"}</span>
                        <span className="text-xs text-[var(--muted-foreground)] ml-2">{a.drive.title}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge tone={a.status === "applied" ? "success" : a.status === "shortlisted" ? "warning" : "destructive"}>
                          {a.status}
                        </Badge>
                        <span className="text-xs text-[var(--muted-foreground)]">
                          {a.applied_at ? new Date(a.applied_at).toLocaleDateString() : ""}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Offers */}
          {placements.data.offers.length > 0 && (
            <Card className="card-shell">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">
                  Placement Offers ({placements.data.offers.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col gap-3">
                  {placements.data.offers.map((o) => (
                    <div key={o.id} className="rounded-lg border border-l-4 border-l-amber-400 border-[var(--border)] bg-amber-50/50 px-4 py-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium">{o.drive.company ?? "Unknown"}</p>
                          <p className="text-xs text-[var(--muted-foreground)]">{o.drive.title} · Round: {o.round_reached}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-[var(--primary)]">{o.offered_ctc} LPA</p>
                          <Badge tone={offerStatusTone(o.offer_status)}>{o.offer_status}</Badge>
                        </div>
                      </div>
                      {o.offer_status === "offered" && !o.decided_at && (
                        <div className="mt-3 flex gap-2">
                          <Button size="sm" onClick={() => decideMut.mutate({ id: o.id, decision: "accepted" })} disabled={decideMut.isPending}>
                            <CheckCircle2 className="h-3 w-3 mr-1" /> Accept
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => decideMut.mutate({ id: o.id, decision: "rejected" })} disabled={decideMut.isPending}>
                            <XCircle className="h-3 w-3 mr-1" /> Reject
                          </Button>
                        </div>
                      )}
                      {o.decided_at && (
                        <p className="mt-2 text-xs text-[var(--muted-foreground)]">
                          Decided on {new Date(o.decided_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Shortlists */}
          {placements.data.shortlists.length > 0 && (
            <Card className="card-shell">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">
                  Shortlist Notifications ({placements.data.shortlists.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col gap-2">
                  {placements.data.shortlists.map((s) => (
                    <div key={s.id} className="rounded-lg border border-l-4 border-l-amber-400 border-[var(--border)] bg-amber-50/50 px-3 py-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{s.title}</span>
                        <span className="text-xs text-[var(--muted-foreground)]">
                          {s.created_at ? new Date(s.created_at).toLocaleDateString() : "—"}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">{s.body}</p>
                      {s.drive.company && (
                        <p className="mt-1 text-xs">{s.drive.company}{s.drive.drive_date ? ` · ${s.drive.drive_date}` : ""}</p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <p className="text-xs text-[var(--muted-foreground)]">{placements.data.note}</p>
        </div>
      )}
    </div>
  );
}
