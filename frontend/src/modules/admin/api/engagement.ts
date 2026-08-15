import { api } from "@/core/lib/api";

export interface ProjectRow {
  id: string;
  title: string;
  lead_name: string;
  department: string;
  status: string;
  funding_amount: number;
  publications: number;
  start_year: number;
}

export interface ResearchReport {
  projects: ProjectRow[];
  total_projects: number;
  total_funding: number;
  total_publications: number;
  status_counts: Record<string, number>;
  by_department: { department: string; projects: number; funding: number; publications: number }[];
}

export interface PartnerRow {
  id: string;
  name: string;
  sector: string;
  contact_person: string;
  mous: number;
  active: boolean;
  placement_hires: number;
}

export interface IndustryReport {
  partners: PartnerRow[];
  total_partners: number;
  active_partners: number;
  total_mous: number;
  total_hires: number;
  sectors: { sector: string; partners: number }[];
  companies_from_placement: number;
}

export const engagementApi = {
  research: (token: string) => api<ResearchReport>("/admin/research", {}, token),
  createProject: (
    body: { title: string; lead_name?: string; department?: string; status?: string; funding_amount?: number; publications?: number; start_year?: number },
    token: string
  ) => api<ProjectRow>("/admin/research", { method: "POST", body: JSON.stringify(body) }, token),

  industry: (token: string) => api<IndustryReport>("/admin/industry", {}, token),
  createPartner: (
    body: { name: string; sector?: string; contact_person?: string; mous?: number; active?: boolean; placement_hires?: number },
    token: string
  ) => api<PartnerRow>("/admin/industry", { method: "POST", body: JSON.stringify(body) }, token),
};
