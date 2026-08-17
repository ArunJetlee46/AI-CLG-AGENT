import { api } from "@/core/lib/api";

export interface FacultyProfile {
  staff_id: string;
  department: string;
  max_hours: number;
  courses: { course_code: string; title: string; credits: number }[];
  course_count: number;
  student_count: number;
  teaching_hours: number;
}

export interface CourseSummary {
  course_code: string;
  title: string;
  enrolled: number;
  avg_marks: number | null;
  highest: number | null;
  lowest: number | null;
  pass_rate: number;
  at_risk_count: number;
  strong_count: number;
  attendance_trend: number;
}

export interface FacultyOverview {
  student_count: number;
  rows: number;
  summary: {
    students: number;
    rows: number;
    average: number | null;
    highest: number | null;
    lowest: number | null;
    pass_rate: number;
    strong: number;
    average_band: number;
    at_risk: number;
  };
  courses: CourseSummary[];
  trends: { course_code: string; title: string; detail: string }[];
}

export interface AtRiskStudent {
  student_id: string;
  course_code: string;
  course_title: string;
  gpa: number;
  attendance_rate: number;
  marks: number | null;
  grade: string;
  probability: number;
  risk_level: string;
  reasons: string[];
}

export interface CourseHealth {
  course_code: string;
  course_title: string;
  exists: boolean;
  authorized: boolean;
  enrolled: number;
  health_score: number | null;
  band: string;
  components: { attendance: number; performance: number; pass_rate: number; failure_rate: number };
  drivers: string[];
}

export interface AttendanceReport {
  course_code: string;
  course_title: string;
  exists: boolean;
  authorized: boolean;
  threshold: number;
  enrolled: number;
  below_count: number;
  students: { student_id: string; attendance_rate: number; gpa: number; grade: string }[];
}

export interface InterventionProposal {
  approval_id: string;
  status: string;
  message: string;
}

export interface InterventionRow {
  id: string;
  status: string;
  student_id: string;
  course_code: string;
  plan_text: string;
  created_at: string;
}

export interface LearningOutcome {
  area: string;
  mastery: number;
  band: string;
  detail: string;
}

export interface CourseOutcomes {
  course_code: string;
  title: string;
  enrolled: number;
  distribution: { high: number; medium: number; low: number };
  outcomes: LearningOutcome[];
  weakest_area: string;
}

export interface LearningOutcomes {
  staff_id: string;
  courses: CourseOutcomes[];
}

export interface RemedialStep {
  kind: string;
  priority: string;
  action: string;
  metric: string;
}

export interface RemedialPlan {
  exists: boolean;
  detail?: string;
  student_id?: string;
  course_code?: string;
  course_title?: string;
  risk_level?: string;
  probability?: number;
  profile?: { gpa: number; attendance_rate: number; marks: number | null; grade: string };
  steps?: RemedialStep[];
  review_after_days?: number;
}

export interface HighPerformer {
  student_id: string;
  gpa: number;
  attendance_rate: number;
  avg_marks: number | null;
  courses: string[];
  score: number;
  band: string;
  reasons: string[];
}

export interface ResearchCandidate {
  student_id: string;
  gpa: number;
  avg_marks: number | null;
  score: number;
  courses: string[];
  suggested_area: string;
  rationale: string;
}

export interface ResearchRecommendations {
  staff_id: string;
  candidates: ResearchCandidate[];
}

export interface ScheduleSlot {
  course_code: string;
  title: string;
  start: string;
  end: string;
  hours: number;
}

export interface ScheduleDay {
  day: string;
  slots: ScheduleSlot[];
}

export interface FacultySchedule {
  staff_id: string;
  total_hours: number;
  max_hours: number;
  utilization: number;
  overloaded: boolean;
  sessions: number;
  days: ScheduleDay[];
  advisory: string;
}

export interface CourseReport {
  course_code: string;
  course_title: string;
  generated_on: string;
  health_score: number | null;
  band: string;
  enrolled: number;
  attendance: number;
  pass_rate: number;
  distribution: { outstanding: number; good: number; average: number; below: number };
  top_students: string[];
  at_risk_students: { student_id: string; risk_level: string }[];
  drivers: string[];
  narrative: string;
}

export interface FacultyTwin {
  staff_id: string;
  identity: { department: string; courses: number; students: number; teaching_hours: number; max_hours: number };
  health: { avg_course_health: number; at_risk_count: number; high_performers: number; attendance: number };
  trajectory: { trend: string; reasons: string[] };
  strengths: string[];
  weaknesses: string[];
  next_best_actions: string[];
  generated_at: string;
}

export interface SimilarityPair {
  student_a: string;
  student_b: string;
  similarity: number;
  flag: string;
}

export interface SimilarityResult {
  staff_id: string;
  threshold: number;
  submissions: number;
  pairs: SimilarityPair[];
  note: string;
}

export interface InterventionRecommendation {
  student_id: string;
  course_code: string;
  course_title: string;
  probability: number;
  risk_level: string;
  recommendation: string[];
  proposed_action: string;
}

export interface PaperQuestion {
  qno: number;
  type: string;
  marks: number;
  question: string;
  rubric: string;
}

export interface QuestionPaper {
  staff_id: string;
  provider: string;
  course_code: string;
  course_title: string;
  topic: string;
  difficulty: string;
  total_marks: number;
  questions: PaperQuestion[];
}

export interface LessonPlan {
  staff_id: string;
  provider: string;
  course_code: string;
  course_title: string;
  topic: string;
  duration_minutes: number;
  learning_outcomes: string[];
  structure: { phase: string; time_minutes: number; activity: string }[];
  assessment: string;
  materials: string[];
}

export interface TeachingMaterial {
  staff_id: string;
  provider: string;
  course_code: string;
  course_title: string;
  topic: string;
  format: string;
  summary: string;
  outline: { section: string; points: string[] }[];
}

export interface AssignmentEval {
  staff_id: string;
  provider: string;
  course_code: string;
  score: number;
  max_score: number;
  percentage: number;
  grade: string;
  criteria: { criterion: string; score: number; max_marks: number; comment: string }[];
  overall: string;
}

export interface CodeReview {
  staff_id: string;
  provider: string;
  language: string;
  score: number;
  summary: string;
  strengths: string[];
  issues: { severity: string; line: number; message: string }[];
  suggestions: string[];
}

export interface LabAssistant {
  staff_id: string;
  provider: string;
  question: string;
  answer: string;
  steps: string[];
  safety_note: string;
}

export interface VivaQuestions {
  staff_id: string;
  provider: string;
  course_code: string;
  course_title: string;
  topic: string;
  questions: { qno: number; question: string; focus: string; expected_points: string[] }[];
}

export interface CopilotStage {
  key: string;
  label: string;
  value: number;
  active: boolean;
}

export interface CopilotStatus {
  staff_id: string;
  stages: CopilotStage[];
}

export interface AuditEntry {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  approval_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogResult {
  staff_id: string;
  total: number;
  entries: AuditEntry[];
}

export interface FacultyPlacementStudent {
  student_id: string;
  readiness_score: number;
  band: string;
  placement_probability: number | null;
  drivers: string[];
}

export interface FacultyPlacementOverview {
  staff_id: string;
  method: string;
  students: FacultyPlacementStudent[];
  summary: { total: number; ready: number; needs_improvement: number; not_ready: number };
}

export interface FacultyStudyAnswer {
  staff_id: string;
  answer: string;
  sources: { document: string; page_start: number | null; course_code: string | null; score: number }[];
  retrieved: unknown[];
  grounded: boolean;
}

export const facultyApi = {
  me: (token: string) => api<FacultyProfile>("/faculty/me", {}, token),
  overview: (token: string) => api<FacultyOverview>("/faculty/overview", {}, token),
  atRisk: (token: string) => api<AtRiskStudent[]>("/faculty/at-risk", {}, token),
  courseHealth: (code: string, token: string) => api<CourseHealth>(`/faculty/courses/${encodeURIComponent(code)}/health`, {}, token),
  courseAttendance: (code: string, token: string) =>
    api<AttendanceReport>(`/faculty/courses/${encodeURIComponent(code)}/attendance`, {}, token),
  proposeIntervention: (studentId: string, courseCode: string, planText: string, token: string) =>
    api<InterventionProposal>(
      "/faculty/interventions",
      { method: "POST", body: JSON.stringify({ student_id: studentId, course_code: courseCode, plan_text: planText }) },
      token
    ),
  interventions: (token: string) => api<InterventionRow[]>("/faculty/interventions", {}, token),
  decide: (id: string, decision: string, token: string) =>
    api<{ ok: boolean; message: string }>(
      `/approvals/${id}`,
      { method: "POST", body: JSON.stringify({ decision, comment: "" }) },
      token
    ),
  learningOutcomes: (token: string) => api<LearningOutcomes>("/faculty/me/learning-outcomes", {}, token),
  highPerformers: (token: string) => api<HighPerformer[]>("/faculty/me/high-performers", {}, token),
  researchRecommendations: (token: string) => api<ResearchRecommendations>("/faculty/me/research-recommendations", {}, token),
  schedule: (token: string) => api<FacultySchedule>("/faculty/me/schedule", {}, token),
  facultyTwin: (token: string) => api<FacultyTwin>("/faculty/me/digital-twin", {}, token),
  interventionRecommendations: (token: string) => api<InterventionRecommendation[]>("/faculty/me/intervention-recommendations", {}, token),
  courseReport: (code: string, token: string) => api<CourseReport>(`/faculty/courses/${encodeURIComponent(code)}/report`, {}, token),
  remedialPlan: (code: string, studentId: string, token: string) =>
    api<RemedialPlan>(`/faculty/courses/${encodeURIComponent(code)}/remedial?student_id=${encodeURIComponent(studentId)}`, {}, token),
  similarity: (submissions: { student_id: string; text: string }[], threshold: number, token: string) =>
    api<SimilarityResult>("/faculty/similarity", { method: "POST", body: JSON.stringify({ submissions, threshold }) }, token),
  questionPaper: (params: { course_code?: string; topic?: string; difficulty?: string; count?: number }, token: string) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return api<QuestionPaper>(`/faculty/tools/question-paper${qs.toString() ? `?${qs.toString()}` : ""}`, {}, token);
  },
  lessonPlan: (body: { course_code?: string; topic: string; duration_minutes?: number }, token: string) =>
    api<LessonPlan>("/faculty/tools/lesson-plan", { method: "POST", body: JSON.stringify(body) }, token),
  teachingMaterial: (body: { course_code?: string; topic: string; format?: string }, token: string) =>
    api<TeachingMaterial>("/faculty/tools/teaching-material", { method: "POST", body: JSON.stringify(body) }, token),
  assignmentEval: (body: { course_code?: string; assignment_brief?: string; rubric?: string; submission: string }, token: string) =>
    api<AssignmentEval>("/faculty/tools/assignment-eval", { method: "POST", body: JSON.stringify(body) }, token),
  codeReview: (body: { language?: string; code: string }, token: string) =>
    api<CodeReview>("/faculty/tools/code-review", { method: "POST", body: JSON.stringify(body) }, token),
  labAssistant: (body: { question: string }, token: string) =>
    api<LabAssistant>("/faculty/tools/lab-assistant", { method: "POST", body: JSON.stringify(body) }, token),
  vivaQuestions: (params: { course_code?: string; topic?: string; count?: number }, token: string) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return api<VivaQuestions>(`/faculty/tools/viva-questions${qs.toString() ? `?${qs.toString()}` : ""}`, {}, token);
  },
  copilotStatus: (token: string) => api<CopilotStatus>("/faculty/copilot-status", {}, token),
  auditLog: (token: string, limit = 50, offset = 0) =>
    api<AuditLogResult>(`/faculty/me/audit?limit=${limit}&offset=${offset}`, {}, token),
  placementOverview: (token: string) => api<FacultyPlacementOverview>("/faculty/me/placement-overview", {}, token),
  askStudyAssistant: (token: string, question: string) =>
    api<FacultyStudyAnswer>("/faculty/me/ask", { method: "POST", body: JSON.stringify({ question }) }, token),
};
