import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Handshake, Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

export function AdminIndustry() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [sector, setSector] = useState("IT");

  const list = useQuery({ queryKey: ["admin-industry"], queryFn: () => adminApi.industry(token!), enabled: !!token });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-industry"] });

  const create = useMutation({
    mutationFn: (b: { name: string; sector?: string }) => adminApi.createPartner(b, token!),
    onSuccess: () => { invalidate(); setName(""); },
  });

  const r = list.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Industry Intelligence" subtitle="Partner engagement, MoUs and placement absorption" icon={Handshake} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Partners" value={r?.total_partners} icon={Building2} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Active" value={r?.active_partners} icon={Building2} accent="bg-green-100 text-green-600" />
        <StatCard label="MoUs signed" value={r?.total_mous} icon={Building2} accent="bg-violet-100 text-violet-600" />
        <StatCard label="Placement hires" value={r?.total_hires} sub={`${r?.companies_from_placement ?? 0} companies from placement module`} icon={Building2} accent="bg-amber-100 text-amber-600" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Plus className="h-4 w-4" /> Add Partner</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Company
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Corp" className="w-52" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Sector
            <select value={sector} onChange={(e) => setSector(e.target.value)} className="h-10 rounded-md border border-[var(--border)] bg-transparent px-3 text-sm">
              {["IT", "Manufacturing", "Healthcare", "Finance", "Education", "Telecom", "Energy", "Agriculture"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
          <Button disabled={!name || create.isPending} onClick={() => create.mutate({ name, sector })}>
            Add
          </Button>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Partners</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                  <th className="pb-2">Company</th>
                  <th className="pb-2">Sector</th>
                  <th className="pb-2 text-right">MoUs</th>
                  <th className="pb-2 text-right">Hires</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {(r?.partners ?? []).map((p) => (
                  <tr key={p.id} className="border-b border-[var(--border)]">
                    <td className="py-2 font-medium">{p.name}</td>
                    <td className="py-2 text-[var(--muted-foreground)]">{p.sector}</td>
                    <td className="py-2 text-right">{p.mous}</td>
                    <td className="py-2 text-right">{p.placement_hires}</td>
                    <td className="py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${p.active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                        {p.active ? "ACTIVE" : "INACTIVE"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sectors</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {(r?.sectors ?? []).map((s) => (
              <div key={s.sector} className="flex items-center gap-2 border-b border-[var(--border)] pb-2 text-sm">
                <span className="w-40">{s.sector}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--muted)]">
                  <span className="block h-full rounded-full bg-[var(--primary)]" style={{ width: `${Math.min(100, s.partners * 20)}%` }} />
                </span>
                <span className="w-8 text-right">{s.partners}</span>
              </div>
            ))}
            {(r?.sectors ?? []).length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No partners yet.</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
