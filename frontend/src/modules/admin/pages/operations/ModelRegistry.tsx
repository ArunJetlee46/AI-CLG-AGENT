import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Brain, Plus, Zap } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { toast } from "@/core/components/ui/toast";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

export function AdminModelRegistry() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [version, setVersion] = useState("");

  const list = useQuery({ queryKey: ["admin-models"], queryFn: () => adminApi.models(token!), enabled: !!token });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-models"] });

  const register = useMutation({
    mutationFn: (b: { name: string; version: string }) => adminApi.registerModel(b, token!),
    onSuccess: () => { invalidate(); setName(""); setVersion(""); },
    onError: (err) => toast.error("Register failed", err instanceof Error ? err.message : undefined),
  });
  const activate = useMutation({
    mutationFn: (id: string) => adminApi.activateModel(id, token!),
    onSuccess: invalidate,
    onError: (err) => toast.error("Activation failed", err instanceof Error ? err.message : undefined),
  });

  const active = list.data?.active;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="AI Model Registry" subtitle="Versioned ML model lifecycle and activation" icon={Brain} />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Plus className="h-4 w-4" /> Register Model</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Name
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="placement_xgb" className="w-52" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Version
            <Input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="1.4.0" className="w-36" />
          </label>
          <Button disabled={!name || !version || register.isPending} onClick={() => register.mutate({ name, version })}>
            Register
          </Button>
        </CardContent>
      </Card>

      {active && (
        <div className="flex items-center gap-3 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-800">
          <Zap className="h-4 w-4" />
          Active model: <span className="font-mono">{active.name}@{active.version}</span> (trained {new Date(active.trained_at).toLocaleDateString()})
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Registry ({list.data?.count ?? 0})</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th className="pb-2">Model</th>
                <th className="pb-2">Version</th>
                <th className="pb-2">Path</th>
                <th className="pb-2">Metrics</th>
                <th className="pb-2">Trained</th>
                <th className="pb-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(list.data?.models ?? []).map((m) => (
                <tr key={m.id} className="border-b border-[var(--border)]">
                  <td className="py-2 font-mono text-xs font-medium">{m.name}</td>
                  <td className="py-2 font-mono text-xs">{m.version}</td>
                  <td className="py-2 font-mono text-xs text-[var(--muted-foreground)]">{m.path}</td>
                  <td className="py-2 text-xs text-[var(--muted-foreground)]">{JSON.stringify(m.metrics ?? {})}</td>
                  <td className="py-2 text-[var(--muted-foreground)]">{new Date(m.trained_at).toLocaleDateString()}</td>
                  <td className="py-2 text-right">
                    {m.is_active ? (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">ACTIVE</span>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => activate.mutate(m.id)}>Activate</Button>
                    )}
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
