import { api } from "@/core/lib/api";

export interface AdminCounts {
  students: number;
  faculty: number;
  departments: number;
  courses: number;
}

export interface AdminKpis {
  attendance: number;
  academic_success: number;
  placement: number;
  at_risk: number;
}

export interface AdminCommandCenter {
  counts: AdminCounts;
  kpis: AdminKpis;
  pending_approvals: number;
  active_agents: number;
  system_health: { backend: string; database: string; llm_providers: string };
  execution_enabled: boolean;
}

export interface HealthScore {
  university_health_score: number;
  axes: Record<string, number>;
  weights: Record<string, number>;
  basis: Record<string, number | null>;
}

export interface EarlyWarning {
  id: string;
  severity: string;
  title: string;
  detail: string;
  recommendation: string;
}

export interface DepartmentReport {
  count: number;
  departments: {
    program: string;
    students: number;
    avg_gpa: number;
    attendance: number;
    pass_rate: number;
    failure_rate: number;
    ready_count: number;
    avg_readiness: number;
    placement: number;
    health: number;
    flag: string | null;
  }[];
  all_programs: string[];
}

export interface FacultyWorkloadRow {
  staff_id: string;
  department: string;
  course_count: number;
  student_count: number;
  teaching_hours: number;
  utilization: number;
}

export interface AgentRecord {
  name: string;
  role: string;
  status: string;
  tasks_processed: number;
  success_rate: number;
  errors: number;
  avg_response_time: number | null;
  last_activity: string | null;
}

export interface SafetyState {
  execution_enabled: boolean;
  read_only: boolean;
  execution_allowed: boolean;
}

export interface AdminUser {
  id: string;
  username: string;
  role: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface Announcement {
  id: string;
  title: string;
  body: string;
  audience: string;
  pinned: boolean;
  created_by: string;
  created_role: string;
  created_at: string;
}

export interface ResourceRow {
  id: string;
  name: string;
  resource_type: string;
  capacity: number;
  location: string;
  status: string;
  utilization: number;
  notes: string;
  source: string;
}

export interface ResourcesReport {
  resources: ResourceRow[];
  count: number;
  status_counts: Record<string, number>;
}

export interface BackupRow {
  id: string;
  filename: string;
  kind: string;
  status: string;
  size_bytes: number;
  note: string;
  created_at: string;
}

export interface ModelEntry {
  id: string;
  name: string;
  version: string;
  path: string;
  metrics: Record<string, unknown>;
  is_active: boolean;
  trained_at: string;
}

export interface ModelReport {
  models: ModelEntry[];
  count: number;
  active: ModelEntry | null;
}

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

export interface StudentAnalytics {
  total: number;
  risk_bands: { low: number; medium: number; high: number };
  by_program: { program: string; count: number; avg_gpa: number; avg_readiness: number; at_risk: number }[];
  by_year: { year: number; count: number; at_risk: number }[];
  avg_attendance: number;
  avg_gpa: number;
  avg_marks: number;
  pass_rate: number;
  top_students: { student_id: string; program: string; gpa: number; readiness_score: number; band: string }[];
  bottom_students: { student_id: string; program: string; gpa: number; readiness_score: number; band: string }[];
}

export interface FacultyAnalytics {
  summary: { total_faculty: number; avg_courses: number; avg_hours: number; overloaded: number };
  rows: (FacultyWorkloadRow & { avg_pass_rate: number | null; flag: string | null })[];
}

export interface PlacementOverview {
  funnel: Record<string, unknown>;
  salary: Record<string, unknown>;
  skill_demand: Record<string, unknown>;
  departments: Record<string, unknown>;
  prediction: Record<string, unknown>;
  companies: number;
  drives: number;
}

export interface DropoutAnalytics {
  total: number;
  bands: { high: number; medium: number; low: number };
  high_risk_ratio: number;
  by_program: { program: string; count: number; high_risk: number; avg_risk: number }[];
  top_risk: {
    student_id: string;
    program: string;
    year: number;
    gpa: number;
    attendance_rate: number;
    avg_marks: number;
    backlogs: number;
    dropout_risk: number;
    band: string;
  }[];
  drivers: { avg_attendance: number; avg_gpa: number; avg_backlogs: number };
}

export interface CurriculumReport {
  total_courses: number;
  difficult_courses: {
    course_code: string;
    title: string;
    department: string;
    credits: number;
    prerequisites: string[];
    enrolled: number;
    avg_marks: number;
    failure_rate: number;
    difficult: boolean;
  }[];
  prerequisite_health: { course_code: string; prerequisite: string; gap: number; healthy: boolean }[];
  courses: CurriculumReport["difficult_courses"];
}

export interface EnrollmentForecast {
  historical: { year: number; enrollments: number }[];
  forecast: { year: number; enrollments: number; forecast: boolean }[];
  total_enrollments: number;
  current_enrollments: number;
  by_department: { department: string; enrollments: number }[];
}

export interface AccreditationReport {
  overall_score: number;
  grade: string;
  criteria: Record<string, number>;
  readiness: { metric: string; met: boolean }[];
  met_count: number;
  total_checks: number;
}

export interface SystemHealth {
  overall: string;
  checks: Record<string, { status: string; detail: string }>;
  counts: Record<string, number>;
}

export interface GovernanceReport {
  safety: SafetyState;
  approvals: { pending: number; total: number };
  audit: { events: number; decision_cards: number };
  models: { total: number; active: number };
  recommendations: string[];
}

export interface AuditRow {
  id: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  approval_id: string | null;
  payload: Record<string, unknown>;
  hash: string;
  created_at: string;
}

export interface CopilotResponse {
  question: string;
  intent: string;
  summary: string;
  key_numbers: { label: string; value: string }[];
  suggested_actions: string[];
  citations: string[];
  provider: string;
}

export interface DigitalTwin {
  state: {
    counts: AdminCounts;
    kpis: AdminKpis;
    pending_approvals: number;
    execution_enabled: boolean;
  };
  health: HealthScore;
  subsystems: { key: string; label: string; score: number; trajectory: string; weight: number }[];
  entities: { students: number; faculty: number; courses: number; rooms: number; timetable_entries: number };
  warnings: EarlyWarning[];
  trajectory: string;
}

export interface ScenarioResult {
  baseline: { university_health_score: number; axes: Record<string, number>; kpis: AdminKpis };
  projected: { university_health_score: number; axes: Record<string, number>; kpis: AdminKpis };
  impact: { score_delta: number; per_axis_deltas: Record<string, number> };
  assumptions: string[];
}

export interface TimetableConflict {
  type: string;
  day: string;
  start: string;
  end: string;
  first: string;
  second: string;
}

export interface TimetableConflicts {
  conflicts: TimetableConflict[];
  count: number;
  total_entries: number;
}

export interface TimetableOptimizeResult {
  proposed: {
    course_code: string;
    title: string;
    room_no: string;
    staff_id: string;
    department: string;
    day: string;
    start: string;
    end: string;
    enrolled: number;
    capacity: number;
  }[];
  stats: {
    courses_scheduled: number;
    courses_unassigned: number;
    unassigned: { course_code: string; title: string; reason: string }[];
    room_utilization: number;
    lecturer_utilization: number;
    slots_available: number;
    room_slots: number;
  };
  commit: boolean;
  conflicts_before: number;
}

export interface EvaluationResult {
  course_code: string;
  question: string;
  max_marks: number;
  total_marks: number;
  grade: string;
  criteria: { name: string; max: number; marks: number; comment: string }[];
  feedback: string;
  strengths: string[];
  improvements: string[];
  provider: string;
}

export const adminApi = {
  commandCenter: (token: string) => api<AdminCommandCenter>("/admin/command-center", {}, token),
  healthScore: (token: string) => api<HealthScore>("/admin/health-score", {}, token),
  earlyWarnings: (token: string) => api<EarlyWarning[]>("/admin/early-warnings", {}, token),
  departments: (token: string) => api<DepartmentReport>("/admin/departments", {}, token),
  facultyWorkload: (token: string, limit = 20) =>
    api<FacultyWorkloadRow[]>(`/admin/faculty-workload?limit=${limit}`, {}, token),
  agents: (token: string) => api<AgentRecord[]>("/admin/agents", {}, token),
  safety: (token: string) => api<SafetyState>("/admin/safety", {}, token),
  setSafety: (body: { execution_enabled: boolean; read_only: boolean }, token: string) =>
    api<SafetyState>("/admin/safety", { method: "POST", body: JSON.stringify(body) }, token),

  users: (token: string) => api<AdminUser[]>("/admin/users", {}, token),
  createUser: (body: { username: string; password: string; role: string; email?: string }, token: string) =>
    api<AdminUser>("/admin/users", { method: "POST", body: JSON.stringify(body) }, token),
  updateUser: (id: string, body: { role?: string; is_active?: boolean; password?: string }, token: string) =>
    api<AdminUser>(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }, token),

  announcements: (token: string) => api<Announcement[]>("/admin/announcements", {}, token),
  createAnnouncement: (body: { title: string; body: string; audience?: string; pinned?: boolean }, token: string) =>
    api<Announcement>("/admin/announcements", { method: "POST", body: JSON.stringify(body) }, token),
  deleteAnnouncement: (id: string, token: string) =>
    api<{ ok: boolean }>(`/admin/announcements/${id}`, { method: "DELETE" }, token),

  resources: (token: string) => api<ResourcesReport>("/admin/resources", {}, token),
  createResource: (
    body: { name: string; resource_type?: string; capacity?: number; location?: string; status?: string; utilization?: number; notes?: string },
    token: string
  ) => api<ResourceRow>("/admin/resources", { method: "POST", body: JSON.stringify(body) }, token),
  updateResource: (id: string, body: { status?: string; utilization?: number }, token: string) =>
    api<ResourceRow>(`/admin/resources/${id}`, { method: "PATCH", body: JSON.stringify(body) }, token),

  backups: (token: string) => api<BackupRow[]>("/admin/backups", {}, token),
  createBackup: (token: string) => api<BackupRow & { snapshot?: Record<string, number> }>("/admin/backups", { method: "POST" }, token),
  restoreBackup: (id: string, token: string) =>
    api<{ ok: boolean; message: string }>(`/admin/backups/${id}/restore`, { method: "POST" }, token),

  models: (token: string) => api<ModelReport>("/admin/models", {}, token),
  registerModel: (body: { name: string; version: string; path?: string; metrics?: Record<string, unknown> }, token: string) =>
    api<ModelEntry>("/admin/models", { method: "POST", body: JSON.stringify(body) }, token),
  activateModel: (id: string, token: string) =>
    api<ModelEntry>(`/admin/models/${id}/activate`, { method: "POST" }, token),

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

  studentAnalytics: (token: string) => api<StudentAnalytics>("/admin/analytics/students", {}, token),
  facultyAnalytics: (token: string) => api<FacultyAnalytics>("/admin/analytics/faculty", {}, token),
  placementAnalytics: (token: string) => api<PlacementOverview>("/admin/analytics/placement", {}, token),
  kpis: (token: string) => api<AdminCommandCenter & { university_health_score: number; axes: Record<string, number>; basis: Record<string, number | null> }>("/admin/analytics/kpis", {}, token),
  dropoutAnalytics: (token: string) => api<DropoutAnalytics>("/admin/analytics/dropout", {}, token),
  curriculum: (token: string) => api<CurriculumReport>("/admin/analytics/curriculum", {}, token),
  enrollmentForecast: (token: string) => api<EnrollmentForecast>("/admin/analytics/enrollment-forecast", {}, token),
  accreditation: (token: string) => api<AccreditationReport>("/admin/analytics/accreditation", {}, token),

  systemHealth: (token: string) => api<SystemHealth>("/admin/system-health", {}, token),
  governance: (token: string) => api<GovernanceReport>("/admin/governance", {}, token),

  audit: (token: string, limit = 100) => api<AuditRow[]>(`/audit?limit=${limit}`, {}, token),
  approvals: (token: string, status = "pending") => api<{ id: string; intent: string; payload: Record<string, unknown>; status: string; created_at: string }[]>(`/approvals?status=${status}`, {}, token),
  decideApproval: (id: string, decision: "approve" | "reject", comment: string, token: string) =>
    api<{ ok: boolean }>(`/approvals/${id}`, { method: "POST", body: JSON.stringify({ decision, comment }) }, token),

  copilot: (question: string, token: string) =>
    api<CopilotResponse>("/admin/copilot", { method: "POST", body: JSON.stringify({ question }) }, token),
  digitalTwin: (token: string) => api<DigitalTwin>("/admin/digital-twin", {}, token),
  runScenario: (
    body: { attendance_delta: number; pass_rate_delta: number; placement_delta: number; readiness_delta: number; interventions: number },
    token: string
  ) => api<ScenarioResult>("/admin/digital-twin/scenarios", { method: "POST", body: JSON.stringify(body) }, token),
  timetableConflicts: (token: string) => api<TimetableConflicts>("/admin/timetable/conflicts", {}, token),
  optimizeTimetable: (body: { commit?: boolean; start_hour?: number; end_hour?: number; slot_minutes?: number }, token: string) =>
    api<TimetableOptimizeResult>("/admin/timetable/optimize", { method: "POST", body: JSON.stringify(body) }, token),
  evaluate: (
    body: { course_code?: string; question: string; rubric?: string; answer: string; max_marks?: number },
    token: string
  ) => api<EvaluationResult>("/admin/evaluation", { method: "POST", body: JSON.stringify(body) }, token),
};
