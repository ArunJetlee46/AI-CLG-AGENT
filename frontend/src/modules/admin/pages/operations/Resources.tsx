import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Boxes, Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

const statusStyles: Record<string, string> = {
  available: "bg-green-100 text-green-700",
  in_use: "bg-sky-100 text-sky-700",
  maintenance: "bg-amber-100 text-amber-700",
};

export function AdminResources() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [type, setType] = useState("classroom");
  const [location, setLocation] = useState("");

  const list = useQuery({ queryKey: ["admin-resources"], queryFn: () => adminApi.resources(token!), enabled: !!token });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-resources"] });

  const create = useMutation({
    mutationFn: (b: { name: string; resource_type?: string; location?: string }) => adminApi.createResource(b, token!),
    onSuccess: () => { invalidate(); setName(""); setLocation(""); },
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: { status?: string; utilization?: number } }) => adminApi.updateResource(id, body, token!),
    onSuccess: invalidate,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Campus Resource Management" subtitle="Rooms, labs and facilities utilization" icon={Boxes} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard label="Resources" value={list.data?.count} icon={Boxes} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Available" value={list.data?.status_counts.available} icon={Boxes} accent="bg-green-100 text-green-600" />
        <StatCard label="In use" value={list.data?.status_counts.in_use} icon={Boxes} accent="bg-violet-100 text-violet-600" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Plus className="h-4 w-4" /> Add Resource</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Name
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Seminar Hall A" className="w-52" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Type
            <select value={type} onChange={(e) => setType(e.target.value)} className="h-10 rounded-md border border-[var(--border)] bg-transparent px-3 text-sm">
              <option value="classroom">Classroom</option>
              <option value="laboratory">Laboratory</option>
              <option value="auditorium">Auditorium</option>
              <option value="library">Library</option>
              <option value="server">Server</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Location
            <Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Block C, Floor 2" className="w-52" />
          </label>
          <Button disabled={!name || create.isPending} onClick={() => create.mutate({ name, resource_type: type, location })}>
            Add
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th className="pb-2">Resource</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">Location</th>
                <th className="pb-2 text-right">Capacity</th>
                <th className="pb-2 text-right">Utilization</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {(list.data?.resources ?? []).map((r) => (
                <tr key={r.id} className="border-b border-[var(--border)]">
                  <td className="py-2 font-medium">{r.name}</td>
                  <td className="py-2 capitalize text-[var(--muted-foreground)]">{r.resource_type}</td>
                  <td className="py-2 text-[var(--muted-foreground)]">{r.location ?? "—"}</td>
                  <td className="py-2 text-right">{r.capacity}</td>
                  <td className="py-2 text-right">
                    {r.source === "live"
                      ? <select value={r.utilization} onChange={(e) => update.mutate({ id: r.id, body: { utilization: Number(e.target.value) } })} className="rounded border border-[var(--border)] bg-transparent px-1 text-xs">
                          {[0, 25, 50, 75, 100].map((v) => <option key={v} value={v}>{v}%</option>)}
                        </select>
                      : `${r.utilization}%`}
                  </td>
                  <td className="py-2">
                    {r.source === "live"
                      ? <select value={r.status} onChange={(e) => update.mutate({ id: r.id, body: { status: e.target.value } })} className={`rounded-full px-2 py-0.5 text-xs font-semibold ${statusStyles[r.status] ?? "bg-[var(--muted)]"}`}>
                          <option value="available">available</option>
                          <option value="in_use">in_use</option>
                          <option value="maintenance">maintenance</option>
                        </select>
                      : <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${statusStyles[r.status] ?? "bg-[var(--muted)]"}`}>{r.status}</span>}
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
