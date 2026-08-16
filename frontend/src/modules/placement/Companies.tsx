import { useQuery } from "@tanstack/react-query";
import { Building2 } from "lucide-react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { placementApi } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

export function Companies() {
  const token = useAuthStore((s) => s.token);
  const companies = useQuery({ queryKey: ["pl-companies"], queryFn: () => placementApi.companies(token!), enabled: !!token });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Company Relationship Management" subtitle="Every partner company, its drives and recorded selections" icon={Building2} accent="bg-sky-100 text-sky-600" />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {(companies.data ?? []).map((c) => (
          <Card key={c.id} className="card-shell">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Building2 className="h-4 w-4" /> {c.name}
                <Badge tone="neutral" className="ml-auto">{c.sector || "sector n/a"}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-1.5 text-sm">
              <p className="text-xs text-[var(--muted-foreground)]">{c.location}{c.location ? " · " : ""}{c.contact_email}{c.contact_phone ? ` · ${c.contact_phone}` : ""}</p>
              <div className="mt-1 flex gap-3">
                <span><strong>{c.drives}</strong> drive(s)</span>
                <span><strong>{c.selections}</strong> selection(s)</span>
              </div>
              {c.notes && <p className="mt-1 text-xs text-[var(--muted-foreground)]">{c.notes}</p>}
            </CardContent>
          </Card>
        ))}
      </div>
      {companies.data?.length === 0 && (
        <p className="text-sm text-[var(--muted-foreground)]">
          No companies yet — add one from the <Link to="/placement/jd" className="text-[var(--primary)] hover:underline">JD Analyzer</Link> page.
        </p>
      )}
    </div>
  );
}
