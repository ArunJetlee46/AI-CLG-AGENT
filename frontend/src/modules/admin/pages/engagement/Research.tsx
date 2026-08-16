import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { StatCard } from "@/core/components/StatCard";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi } from "@/modules/admin/api";

const statusStyles: Record<string, string> = {
  ongoing: "bg-sky-100 text-sky-700",
  completed: "bg-green-100 text-green-700",
  proposal: "bg-amber-100 text-amber-700",
  funded: "bg-violet-100 text-violet-700",
};

export function AdminResearch() {
  const token = useAuthStore((s) => s.token);
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [lead, setLead] = useState("");

  const list = useQuery({ queryKey: ["admin-research"], queryFn: () => adminApi.research(token!), enabled: !!token });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-research"] });

  const create = useMutation({
    mutationFn: (b: { title: string; lead_name?: string }) => adminApi.createProject(b, token!),
    onSuccess: () => { invalidate(); setTitle(""); setLead(""); },
  });

  const r = list.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Research Management" subtitle="Projects, funding and publications" icon={FlaskConical} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Projects" value={r?.total_projects} icon={FlaskConical} accent="bg-sky-100 text-sky-600" />
        <StatCard label="Total funding" value={r?.total_funding ? `₹${Number(r.total_funding).toLocaleString()}` : null} icon={FlaskConical} accent="bg-emerald-100 text-emerald-600" />
        <StatCard label="Publications" value={r?.total_publications} icon={FlaskConical} accent="bg-violet-100 text-violet-600" />
        <StatCard label="Ongoing" value={r?.status_counts.ongoing ?? 0} icon={FlaskConical} accent="bg-amber-100 text-amber-600" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Plus className="h-4 w-4" /> Register Project</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Title
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="AI-assisted crop monitoring" className="w-72" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Lead researcher
            <Input value={lead} onChange={(e) => setLead(e.target.value)} placeholder="optional" className="w-48" />
          </label>
          <Button disabled={!title || create.isPending} onClick={() => create.mutate({ title, lead_name: lead || undefined })}>
            Register
          </Button>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Projects</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                  <th className="pb-2">Title</th>
                  <th className="pb-2">Lead</th>
                  <th className="pb-2 text-right">Funding</th>
                  <th className="pb-2 text-right">Pub.</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {(r?.projects ?? []).map((p) => (
                  <tr key={p.id} className="border-b border-[var(--border)]">
                    <td className="py-2 font-medium">
                      <span className="line-clamp-1 max-w-[220px]">{p.title}</span>
                    </td>
                    <td className="py-2 text-[var(--muted-foreground)]">{p.lead_name ?? "—"}</td>
                    <td className="py-2 text-right">{p.funding_amount ? `₹${Number(p.funding_amount).toLocaleString()}` : "—"}</td>
                    <td className="py-2 text-right">{p.publications}</td>
                    <td className="py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${statusStyles[p.status] ?? "bg-[var(--muted)]"}`}>{p.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>By Department</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {(r?.by_department ?? []).map((d) => (
              <div key={d.department} className="flex items-center gap-2 border-b border-[var(--border)] pb-2 text-sm">
                <span className="w-52 truncate">{d.department}</span>
                <span className="text-xs text-[var(--muted-foreground)]">{d.projects} projects</span>
                <span className="text-xs text-[var(--muted-foreground)]">{d.publications} pubs</span>
                <span className="ml-auto text-xs font-semibold">₹{Number(d.funding).toLocaleString()}</span>
              </div>
            ))}
            {(r?.by_department ?? []).length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No projects yet.</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
