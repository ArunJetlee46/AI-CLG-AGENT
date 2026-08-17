import { api } from "@/core/lib/api";

export interface PlacementReady {
  student_id: string;
  program: string;
  year: number;
  gpa: number;
  attendance_rate: number;
  avg_marks: number;
  backlogs: number;
  readiness_score: number;
  band: "ready" | "needs_improvement" | "not_ready";
  components: { academic: number; attendance: number; aptitude: number; consistency: number };
  placement_probability: number;
  unplaced_risk: number;
  drivers: string[];
}

export interface PlacementOverview {
  total_students: number;
  predicted_placement_rate: number | null;
  avg_readiness: number | null;
  distribution: { ready: number; needs_improvement: number; not_ready: number };
  funnel: { ready: number; needs_improvement: number; not_ready: number; at_risk: number };
  departments: { program: string; students: number; ready: number; avg_readiness: number; avg_gpa: number }[];
}

export interface AtRiskCandidate {
  student_id: string;
  program: string;
  gpa: number;
  attendance_rate: number;
  backlogs: number;
  readiness_score: number;
  placement_probability: number;
  risk_level: "high" | "medium";
  reasons: string[];
}

export interface ShortlistCandidate {
  student_id: string;
  program: string;
  gpa: number;
  backlogs: number;
  readiness_score: number;
  match_score: number;
  skills_matched: string[];
  gates: { gpa_ok: boolean; backlogs_ok: boolean };
}

export interface PlacementReport {
  generated_at: string;
  method: string;
  total_students: number;
  predicted_placement_rate: number | null;
  avg_readiness: number | null;
  distribution: { ready: number; needs_improvement: number; not_ready: number };
  departments: { program: string; students: number; ready: number; avg_readiness: number; avg_gpa: number }[];
  note: string;
}

export interface FlowStatus {
  generated_at: string;
  total_students: number;
  cohort_years: Record<string, number>;
  stages: { key: string; label: string; value: number }[];
}

export interface JDAnalysis {
  skills: string[];
  role_type: string;
  min_gpa: number;
  max_backlogs: number;
  year_required: number;
  ctc_min: number;
  ctc_max: number;
  location: string;
  mode: string;
  word_count: number;
  method: string;
}

export interface CompanyCreateBody {
  name: string;
  sector: string;
  location: string;
  contact_email: string;
  contact_phone: string;
  notes: string;
}

export interface CompanyRow extends CompanyCreateBody {
  id: string;
  created_at: string;
  drives: number;
  selections: number;
}

export interface JdCreateBody {
  company_id: string;
  title: string;
  raw_text: string;
  min_gpa?: number | null;
  max_backlogs?: number | null;
  ctc_min?: number | null;
  ctc_max?: number | null;
  openings?: number | null;
}

export interface JdRow {
  id: string;
  company_id: string;
  title: string;
  skills: string[];
  role_type: string;
  min_gpa: number;
  max_backlogs: number;
  year_required: number;
  ctc_min: number;
  ctc_max: number;
  openings: number;
  location: string;
  mode: string;
  status: string;
  created_at: string;
  drives: number;
}

export interface MatchCandidate {
  student_id: string;
  program: string;
  year: number;
  gpa: number;
  backlogs: number;
  readiness_score: number;
  placement_probability: number;
  skills_matched: string[];
  match_score: number;
  gates: { gpa_ok: boolean; backlogs_ok: boolean; year_ok: boolean };
}

export interface MatchingResult {
  jd_id: string;
  title: string;
  required_skills: string[];
  eligible_count: number;
  candidates: MatchCandidate[];
}

export interface DriveCreateBody {
  title: string;
  company_id: string;
  jd_id?: string | null;
  drive_date: string;
  mode: string;
  location: string;
}

export interface RoundCreateBody {
  name: string;
  round_order: number;
  round_date: string;
}

export interface RoundRow {
  id: string;
  name: string;
  round_order: number;
  round_date: string;
  status: string;
}

export interface SelectionRow {
  id: string;
  student_id: string;
  round_reached: string;
  offered_ctc: number;
  offer_status: string;
}

export interface DriveRow {
  id: string;
  title: string;
  company: string;
  company_id: string;
  jd_id: string | null;
  drive_date: string;
  mode: string;
  location: string;
  status: string;
  rounds: RoundRow[];
  selections: SelectionRow[];
  notified: number;
}

export interface PipelineResult {
  drive: DriveRow;
  company: string;
  rounds: string[];
  funnel: { stage: string; count: number }[];
  selections: SelectionRow[];
  offer_rate_pct: number;
}

export interface SelectionCreateBody {
  drive_id: string;
  student_id: string;
  round_reached: string;
  offered_ctc: number;
  offer_status: string;
}

export interface FunnelResult {
  cohort: number;
  eligible: number;
  shortlisted: number;
  offers: number;
  joined: number;
  ready: number;
  at_risk: number;
  conversion: { eligible_pct: number; offer_rate_pct: number; join_rate_pct: number };
  note: string;
}

export interface SalaryResult {
  overall: SalaryAgg;
  by_program: Record<string, SalaryAgg>;
  by_sector: Record<string, SalaryAgg>;
  note: string;
}

export interface SalaryAgg {
  count: number;
  avg_ctc: number | null;
  median_ctc: number | null;
  max_ctc: number | null;
  offered: number;
  joined: number;
}

export interface SkillDemandResult {
  total_jds: number;
  top_skills: { skill: string; demand: number }[];
  sectors: { sector: string; jds: number; top_skills: { skill: string; demand: number }[] }[];
}

export interface GapStudent {
  student_id: string;
  program: string;
  skills: string[];
  gap_skills: string[];
  gap_count: number;
  recommendation: string;
}

export interface GapResult {
  required_skills: string[];
  students: GapStudent[];
  total: number;
}

export interface TrainingPlan {
  student_id: string;
  program: string;
  readiness_score: number;
  placement_probability: number;
  weakest_component: string;
  gap_skills: string[];
  plan: string;
}

export interface AssessmentResult {
  kind: string;
  note: string;
  programs: { program: string; students: number; avg_score: number; pass_rate: number; max_score: number; min_score: number }[];
  overall_avg: number;
  overall_pass_rate: number;
}

export interface DeptRow {
  program: string;
  students: number;
  ready: number;
  avg_readiness: number;
  avg_gpa: number;
  avg_ctc: number | null;
  offers: number;
  joined: number;
}

export interface DeptResult {
  programs: DeptRow[];
}

export interface PredictionResult {
  predicted_placement_rate: number | null;
  cohort_size: number;
  ready_count: number;
  at_risk_count: number;
  trend: { year: number; students: number; predicted_rate: number }[];
  note: string;
}

export interface NotificationEntry {
  id: string;
  student_id: string;
  title: string;
  body: string;
  status: string;
  created_at: string;
}

export interface NotificationResult {
  entries: NotificationEntry[];
  total: number;
  unread: number;
}

export interface FullReport {
  generated_at: string;
  method: string;
  funnel: FunnelResult;
  prediction: PredictionResult;
  departments: DeptRow[];
  salary: SalaryAgg;
  top_skills: { skill: string; demand: number }[];
  high_risk_students: number;
  summary: string;
}

export interface CsvPreviewResult {
  import_type: string;
  filename: string;
  total_rows: number | string;
  preview: Record<string, string>[];
  validation_errors: { row: number; errors: string[] }[];
  error_count: number;
  can_import: boolean;
}

export interface CsvImportResult {
  import_type: string;
  imported: number;
  skipped: number;
  message: string;
}

export const placementApi = {
  overview: (token: string) => api<PlacementOverview>("/placement/overview", {}, token),
  readiness: (token: string, limit = 100) => api<PlacementReady[]>(`/placement/readiness?limit=${limit}`, {}, token),
  atRisk: (token: string, limit = 50) => api<AtRiskCandidate[]>(`/placement/at-risk?limit=${limit}`, {}, token),
  shortlist: (
    spec: { role: string; min_gpa: number; max_backlogs: number; required_skills: string[]; limit: number },
    token: string
  ) =>
    api<{ role: string; eligible_count: number; candidates: ShortlistCandidate[] }>(
      "/placement/shortlist",
      { method: "POST", body: JSON.stringify(spec) },
      token
    ),
  report: (token: string) => api<PlacementReport>("/placement/report", {}, token),
  flowStatus: (token: string) => api<FlowStatus>("/placement/flow-status", {}, token),
  analyzeJd: (text: string, token: string) =>
    api<JDAnalysis>("/placement/jd/analyze", { method: "POST", body: JSON.stringify({ text }) }, token),
  createCompany: (body: CompanyCreateBody, token: string) =>
    api<CompanyRow>("/placement/companies", { method: "POST", body: JSON.stringify(body) }, token),
  companies: (token: string) => api<CompanyRow[]>("/placement/companies", {}, token),
  createJd: (body: JdCreateBody, token: string) =>
    api<JdRow>("/placement/jd", { method: "POST", body: JSON.stringify(body) }, token),
  jds: (token: string, companyId?: string) =>
    api<JdRow[]>(`/placement/jd${companyId ? `?company_id=${companyId}` : ""}`, {}, token),
  matching: (jdId: string, token: string, limit = 200) =>
    api<MatchingResult>(`/placement/matching/${jdId}?limit=${limit}`, {}, token),
  createDrive: (body: DriveCreateBody, token: string) =>
    api<DriveRow>("/placement/drives", { method: "POST", body: JSON.stringify(body) }, token),
  drives: (token: string) => api<DriveRow[]>("/placement/drives", {}, token),
  addRound: (driveId: string, body: RoundCreateBody, token: string) =>
    api<DriveRow>(`/placement/drives/${driveId}/rounds`, { method: "POST", body: JSON.stringify({ ...body, drive_id: driveId }) }, token),
  notify: (driveId: string, studentIds: string[], token: string) =>
    api<{ notified: number }>(
      `/placement/drives/${driveId}/notify`,
      { method: "POST", body: JSON.stringify({ drive_id: driveId, student_ids: studentIds }) },
      token
    ),
  pipeline: (driveId: string, token: string) => api<PipelineResult>(`/placement/drives/${driveId}/pipeline`, {}, token),
  recordSelection: (body: SelectionCreateBody, token: string) =>
    api<DriveRow>("/placement/selections", { method: "POST", body: JSON.stringify(body) }, token),
  funnel: (token: string) => api<FunnelResult>("/placement/funnel", {}, token),
  salary: (token: string) => api<SalaryResult>("/placement/salary", {}, token),
  skillDemand: (token: string) => api<SkillDemandResult>("/placement/skill-demand", {}, token),
  gaps: (token: string) => api<GapResult>("/placement/gaps", {}, token),
  training: (token: string, limit = 50) => api<TrainingPlan[]>(`/placement/training?limit=${limit}`, {}, token),
  codingAnalytics: (token: string) => api<AssessmentResult>("/placement/analytics/coding", {}, token),
  aptitudeAnalytics: (token: string) => api<AssessmentResult>("/placement/analytics/aptitude", {}, token),
  communicationAnalytics: (token: string) => api<AssessmentResult>("/placement/analytics/communication", {}, token),
  departments: (token: string) => api<DeptResult>("/placement/departments", {}, token),
  prediction: (token: string) => api<PredictionResult>("/placement/prediction", {}, token),
  notifications: (token: string) => api<NotificationResult>("/placement/notifications", {}, token),
  markNotificationRead: (id: string, token: string) =>
    api<{ id: string; status: string }>(`/placement/notifications/${id}/read`, { method: "POST" }, token),
  fullReport: (token: string) => api<FullReport>("/placement/report/full", {}, token),
  importPreview: (importType: string, file: File, token: string) => {
    const params = new URLSearchParams({ import_type: importType });
    const form = new FormData();
    form.append("file", file);
    return api<CsvPreviewResult>(
      `/placement/import/preview?${params}`,
      { method: "POST", body: form },
      token
    );
  },
  importConfirm: (importType: string, file: File, token: string) => {
    const params = new URLSearchParams({ import_type: importType });
    const form = new FormData();
    form.append("file", file);
    return api<CsvImportResult>(
      `/placement/import/confirm?${params}`,
      { method: "POST", body: form },
      token
    );
  },
};
