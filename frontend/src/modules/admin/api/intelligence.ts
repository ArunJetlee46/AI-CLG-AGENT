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

export interface GovernanceReport {
  safety: SafetyState;
  approvals: { pending: number; total: number };
  audit: { events: number; decision_cards: number };
  models: { total: number; active: number };
  recommendations: string[];
}

export const intelligenceApi = {
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
  governance: (token: string) => api<GovernanceReport>("/admin/governance", {}, token),
};
