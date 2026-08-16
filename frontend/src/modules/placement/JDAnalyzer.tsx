import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, FileSearch, FileText, Save, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input, Textarea } from "@/core/components/ui/input";
import { Select } from "@/core/components/ui/select";
import { placementApi, type JDAnalysis, type JdRow } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";

export function JDAnalyzer() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();

  const companies = useQuery({ queryKey: ["pl-companies"], queryFn: () => placementApi.companies(token!), enabled: !!token });
  const jds = useQuery({ queryKey: ["pl-jds"], queryFn: () => placementApi.jds(token!), enabled: !!token });

  const [name, setName] = useState("");
  const [sector, setSector] = useState("");
  const [location, setLocation] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const [title, setTitle] = useState("");
  const [companyId, setCompanyId] = useState("");
  const [rawText, setRawText] = useState("");
  const [analysis, setAnalysis] = useState<JDAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [saved, setSaved] = useState<JdRow | null>(null);

  const createCompany = useMutation({
    mutationFn: () =>
      placementApi.createCompany(
        { name, sector, location, contact_email: email, contact_phone: phone, notes: "" },
        token!
      ),
    onSuccess: (row) => {
      setCompanyId(row.id);
      setName("");
      setSector("");
      setLocation("");
      setEmail("");
      setPhone("");
      qc.invalidateQueries({ queryKey: ["pl-companies"] });
    },
  });

  const runAnalyzer = async () => {
    if (!token) return;
    setAnalyzing(true);
    try {
      setAnalysis(await placementApi.analyzeJd(rawText, token));
    } finally {
      setAnalyzing(false);
    }
  };

  const saveJd = useMutation({
    mutationFn: () =>
      placementApi.createJd(
        {
          company_id: companyId,
          title,
          raw_text: rawText,
          min_gpa: analysis?.min_gpa ?? null,
          max_backlogs: analysis?.max_backlogs ?? null,
          ctc_min: analysis?.ctc_min ?? null,
          ctc_max: analysis?.ctc_max ?? null,
          openings: 1,
        },
        token!
      ),
    onSuccess: (row) => {
      setSaved(row);
      setTitle("");
      setRawText("");
      setAnalysis(null);
      qc.invalidateQueries({ queryKey: ["pl-jds"] });
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Job Description Analyzer" subtitle="Upload a JD → the copilot extracts skills, eligibility gates, CTC and role type" icon={FileSearch} accent="bg-emerald-100 text-emerald-600" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><Building2 className="h-4 w-4" /> New company</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Input placeholder="Company name" value={name} onChange={(e) => setName(e.target.value)} />
              <Input placeholder="Sector (Software, Banking…)" value={sector} onChange={(e) => setSector(e.target.value)} />
              <Input placeholder="Location" value={location} onChange={(e) => setLocation(e.target.value)} />
              <Input placeholder="Contact email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="flex items-center gap-2">
              <Input placeholder="Contact phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
              <Button onClick={() => createCompany.mutate()} disabled={!name || createCompany.isPending}>
                {createCompany.isPending ? "Adding…" : "Add company"}
              </Button>
            </div>
            <Select value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
              <option value="">Pick a company for the JD…</option>
              {(companies.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.name} · {c.sector}</option>
              ))}
            </Select>
          </CardContent>
        </Card>

        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><FileText className="h-4 w-4" /> JD text</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Input placeholder="Job title (e.g. Data Scientist Intern)" value={title} onChange={(e) => setTitle(e.target.value)} />
            <Textarea
              className="min-h-[180px] resize-y"
              placeholder={"Paste the full job description…\n\ne.g. Software Engineer Intern. Requires Python, Java, SQL, communication. GPA 3.0, 0 backlogs. CTC 12-18 LPA."}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
            />
            <div className="flex items-center gap-2">
              <Button onClick={runAnalyzer} disabled={analyzing || rawText.length < 20} variant="outline">
                <Sparkles className="mr-1 h-4 w-4" /> {analyzing ? "Analyzing…" : "Analyze JD"}
              </Button>
              <Button onClick={() => saveJd.mutate()} disabled={!title || !companyId || !analysis || saveJd.isPending}>
                <Save className="mr-1 h-4 w-4" /> Save JD
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {analysis && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm"><FileSearch className="h-4 w-4" /> Analysis</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-8">
            <div className="rounded-lg border border-[var(--border)] p-3 text-center">
              <p className="text-lg font-bold">{analysis.role_type}</p>
              <p className="text-[11px] text-[var(--muted-foreground)]">role type</p>
            </div>
            <div className="rounded-lg border border-[var(--border)] p-3 text-center">
              <p className="text-lg font-bold">{analysis.min_gpa}</p>
              <p className="text-[11px] text-[var(--muted-foreground)]">min GPA</p>
            </div>
            <div className="rounded-lg border border-[var(--border)] p-3 text-center">
              <p className="text-lg font-bold">{analysis.max_backlogs}</p>
              <p className="text-[11px] text-[var(--muted-foreground)]">max backlogs</p>
            </div>
            <div className="rounded-lg border border-[var(--border)] p-3 text-center">
              <p className="text-lg font-bold">{analysis.ctc_min ? `${analysis.ctc_min}–${analysis.ctc_max || analysis.ctc_min} LPA` : "—"}</p>
              <p className="text-[11px] text-[var(--muted-foreground)]">CTC</p>
            </div>
            <div className="rounded-lg border border-[var(--border)] p-3 text-center">
              <p className="text-lg font-bold">{analysis.mode}</p>
              <p className="text-[11px] text-[var(--muted-foreground)]">mode</p>
            </div>
            <div className="rounded-lg border border-[var(--border)] p-3 text-center">
              <p className="text-lg font-bold">{analysis.location || "—"}</p>
              <p className="text-[11px] text-[var(--muted-foreground)]">location</p>
            </div>
            <div className="col-span-2 rounded-lg border border-[var(--border)] p-3">
              <p className="text-[11px] text-[var(--muted-foreground)]">skills ({analysis.skills.length})</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {analysis.skills.slice(0, 12).map((s) => (
                  <Badge key={s} tone="neutral">{s}</Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm">Saved job descriptions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {(jds.data ?? []).length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No JDs yet — save one above.</p>}
          {(jds.data ?? []).map((jd) => (
            <div key={jd.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--border)] px-3 py-2">
              <span className="text-sm font-medium">{jd.title}</span>
              <Badge tone="neutral">{jd.role_type}</Badge>
              {jd.skills.slice(0, 5).map((s) => <Badge key={s}>{s}</Badge>)}
              <span className="ml-auto text-xs text-[var(--muted-foreground)]">
                GPA ≥ {jd.min_gpa} · ≤{jd.max_backlogs} AR{jd.ctc_min ? ` · ${jd.ctc_min}–${jd.ctc_max} LPA` : ""}
                <Link to="/placement/matching" className="ml-2 text-[var(--primary)]">Match →</Link>
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      {saved && (
        <p className="text-sm text-green-600">Saved JD “{saved.title}” — go to <Link className="text-[var(--primary)]" to="/placement/matching">matching</Link> to run eligibility + ranking.</p>
      )}
    </div>
  );
}
