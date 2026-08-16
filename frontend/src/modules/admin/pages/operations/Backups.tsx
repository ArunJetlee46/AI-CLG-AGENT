import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DatabaseBackup, HardDriveDownload, RotateCcw } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { toast } from "@/core/components/ui/toast";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

export function AdminBackups() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [msg, setMsg] = useState("");

  const list = useQuery({ queryKey: ["admin-backups"], queryFn: () => adminApi.backups(token!), enabled: !!token });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-backups"] });

  const create = useMutation({
    mutationFn: () => adminApi.createBackup(token!),
    onSuccess: invalidate,
    onError: (err) => toast.error("Snapshot failed", err instanceof Error ? err.message : undefined),
  });
  const restore = useMutation({
    mutationFn: (id: string) => adminApi.restoreBackup(id, token!),
    onSuccess: (r) => { invalidate(); setMsg(r.message); setTimeout(() => setMsg(""), 6000); },
    onError: (err) => toast.error("Restore failed", err instanceof Error ? err.message : undefined),
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Backup & Restore"
        subtitle="Automated snapshot management for the university database"
        icon={DatabaseBackup}
        actions={
          <Button disabled={create.isPending} onClick={() => create.mutate()}>
            <HardDriveDownload className="h-4 w-4" /> Take Snapshot
          </Button>
        }
      />

      {msg && <p className="rounded-lg bg-green-100 px-4 py-2 text-sm font-semibold text-green-700">{msg}</p>}

      <Card>
        <CardHeader>
          <CardTitle>Snapshots ({list.data?.length ?? 0})</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th className="pb-2">Filename</th>
                <th className="pb-2">Kind</th>
                <th className="pb-2 text-right">Size</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Created</th>
                <th className="pb-2 text-right">Restore</th>
              </tr>
            </thead>
            <tbody>
              {(list.data ?? []).map((b) => (
                <tr key={b.id} className="border-b border-[var(--border)]">
                  <td className="py-2 font-mono text-xs">{b.filename}</td>
                  <td className="py-2 capitalize text-[var(--muted-foreground)]">{b.kind}</td>
                  <td className="py-2 text-right">{(b.size_bytes / 1024).toFixed(1)} KB</td>
                  <td className="py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${b.status === "ok" ? "bg-green-100 text-green-700" : b.status === "failed" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                      {b.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-2 text-[var(--muted-foreground)]">{new Date(b.created_at).toLocaleString()}</td>
                  <td className="py-2 text-right">
                    <Button size="sm" variant="outline" disabled={restore.isPending} onClick={() => restore.mutate(b.id)}>
                      <RotateCcw className="h-3 w-3" /> Restore
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
