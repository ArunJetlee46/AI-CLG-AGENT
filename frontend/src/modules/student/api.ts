import { api } from "@/core/lib/api";

export interface StudentCourse {
  course_code: string;
  title: string;
  credits: number;
  marks: number | null;
  grade: string;
  status: "passed" | "failed" | "ongoing";
  attendance_rate: number;
}

export interface StudentProfile {
  student_id: string;
  program: string;
  year: number;
  gpa: number;
  overall_attendance: number;
  avg_marks: number;
  credits_earned: number;
  course_load: number;
  courses: StudentCourse[];
}

export interface SuccessScore {
  student_id: string;
  success_score: number;
  risk_level: string;
  components: { name: string; score: number; weight: number }[];
  drivers: string[];
}

export interface StudentAlert {
  severity: string;
  kind: string;
  course_code: string | null;
  title: string;
  detail: string;
  recommendation: string;
}

export interface CoursePrediction {
  course_code: string;
  title: string;
  credits: number;
  grade: string;
  status: string;
  attendance_rate: number;
  pass_probability: number;
  failure_risk: number;
  risk_level: string;
}

export interface Predictions {
  student_id: string;
  gpa: number;
  projected_gpa: number;
  method: string;
  note: string;
  predictions: CoursePrediction[];
}

export interface AdviseResponse {
  course_code: string;
  course_title: string;
  exists: boolean;
  eligible: boolean;
  reason: string;
  direct_prerequisites: string[];
  unmet_prerequisites: string[];
  chain: string[];
  passed_codes: string[];
}

export interface TodayPlan {
  student_id: string;
  date: string;
  success_score: number;
  risk_level: string;
  plan: { severity: string; kind: string; course_code: string | null; action: string }[];
}

export interface WeaknessArea {
  area: string;
  severity: string;
  detail: string;
  courses: { course_code: string; title: string; evidence: string }[];
  recommendation: string;
}

export interface Weaknesses {
  student_id: string;
  overall_weakness_score: number;
  areas: WeaknessArea[];
  strengths: string[];
}

export interface ElectiveReco {
  course_code: string;
  title: string;
  credits: number;
  department: string;
  match_score: number;
  reason: string;
}

export interface Recommendations {
  student_id: string;
  method: string;
  electives: ElectiveReco[];
  strengthen: { course_code: string; title: string; reason: string }[];
  next_steps: string[];
}

export interface CareerReadiness {
  student_id: string;
  career_readiness_score: number;
  band: string;
  components: { name: string; score: number; weight: number }[];
  drivers: string[];
  strengths: string[];
  areas_to_grow: string[];
}

export interface StudyGroup {
  peer_student_id: string;
  peer_program: string;
  peer_gpa: number;
  shared_courses: {
    course_code: string;
    student_attendance: number;
    peer_attendance: number;
    student_marks: number | null;
    peer_marks: number | null;
  }[];
  complementarity_score: number;
  synergy: string[];
}

export interface StudyGroups {
  student_id: string;
  groups: StudyGroup[];
  note: string;
}

export interface NotificationItem {
  type: string;
  severity: string;
  title: string;
  detail: string;
  action: string;
}

export interface NotificationsResponse {
  student_id: string;
  generated_at: string;
  notifications: NotificationItem[];
}

export interface BadgeInfo {
  id: string;
  name: string;
  description: string;
  earned: boolean;
}

export interface Gamification {
  student_id: string;
  level: number;
  xp: number;
  xp_in_level: number;
  xp_to_next_level: number;
  level_progress: number;
  badges: BadgeInfo[];
}

export interface DigitalTwin {
  student_id: string;
  identity: { program: string; year: number; gpa: number; credits_earned: number; course_load: number };
  health: { success_score: number; risk_level: string; career_readiness: number; weakness_score: number };
  behavior: { attendance: number; pass_rate: number; avg_marks: number };
  trajectory: { trend: string; reasons: string[] };
  strengths: string[];
  weaknesses: string[];
  next_best_actions: string[];
  generated_at: string;
}

export interface ProgressSeriesPoint {
  week: number;
  value: number;
}

export interface CourseTrend {
  course_code: string;
  title: string;
  pass_probability: number | null;
  risk_level: string | null;
  trend: string;
}

export interface ProgressAnalytics {
  student_id: string;
  method: string;
  weeks: number[];
  success_trend: ProgressSeriesPoint[];
  attendance_trend: ProgressSeriesPoint[];
  gpa_trend: ProgressSeriesPoint[];
  course_trends: CourseTrend[];
}

export interface QuizQuestion {
  id: string;
  course_code: string;
  question: string;
  options: string[];
  answer_index: number;
  explanation: string;
}

export interface ExamPrep {
  student_id: string;
  provider: string;
  course_code: string;
  questions: QuizQuestion[];
}

export interface AssistPoint {
  title: string;
  detail: string;
}

export interface AssignmentAssist {
  student_id: string;
  course_code: string;
  provider: string;
  kind: string;
  summary: string;
  points: AssistPoint[];
}

export interface InterviewQuestion {
  student_id: string;
  provider: string;
  role: string;
  question: string;
  focus: string;
  tip: string;
}

export interface InterviewScore {
  student_id: string;
  provider: string;
  score: number;
  strengths: string[];
  weaknesses: string[];
  improvement_tip: string;
}

export interface ResumeATS {
  student_id: string;
  provider: string;
  score: number;
  section_scores: { format: number; content: number; skills: number };
  matched_skills: string[];
  suggestions: string[];
}

export interface ProjectMentor {
  student_id: string;
  provider: string;
  project_title: string;
  milestones: string[];
  advice: string;
  next_action: string;
}

export interface TimetableEntry {
  day: string;
  term: string;
  start_time: string;
  end_time: string;
  course_code: string;
  course_title: string;
  credits: number;
  room: string;
  lecturer: string;
}

export interface MyTimetable {
  student_id: string;
  method: string;
  days: string[];
  entries: TimetableEntry[];
  by_day: Record<string, TimetableEntry[]>;
}

export interface PlacementReadiness {
  student_id: string;
  readiness_score: number;
  band: string;
  components: { name: string; score: number; weight: number }[];
  placement_probability: number | null;
  drivers: string[];
}

export interface DriveInfo {
  id: string | null;
  title: string | null;
  company: string | null;
  company_id?: string;
  drive_date: string | null;
  mode: string | null;
  location: string | null;
  status: string | null;
}

export interface ShortlistNotification {
  id: string;
  drive_id: string | null;
  title: string;
  body: string;
  status: string;
  created_at: string | null;
  drive: DriveInfo;
}

export interface OpenDrive extends DriveInfo {
  applied: boolean;
  notified: boolean;
}

export interface PlacementApplication {
  id: string;
  drive_id: string;
  status: string;
  applied_at: string | null;
  drive: DriveInfo;
}

export interface PlacementOffer {
  id: string;
  drive_id: string;
  round_reached: string;
  offered_ctc: number;
  offer_status: string;
  decided_at: string | null;
  created_at: string | null;
  drive: DriveInfo;
}

export interface ResumeInfo {
  id: string;
  filename: string;
  skills: string[];
  uploaded_at: string | null;
}

export interface MyPlacements {
  student_id: string;
  method: string;
  readiness: PlacementReadiness | null;
  shortlists: ShortlistNotification[];
  open_drives: OpenDrive[];
  applications: PlacementApplication[];
  offers: PlacementOffer[];
  resume: ResumeInfo | null;
  note: string;
}

export interface StudySource {
  document: string;
  page_start: number | null;
  page_end: number | null;
  course_code: string | null;
  course_title: string | null;
  regulation: string | null;
  programme: string | null;
  score: number;
}

export interface StudyAnswer {
  student_id: string;
  answer: string;
  sources: StudySource[];
  retrieved: unknown[];
  grounded: boolean;
}

export const studentApi = {
  profile: (token: string) => api<StudentProfile>("/students/me", {}, token),
  successScore: (token: string) => api<SuccessScore>("/students/me/success-score", {}, token),
  alerts: (token: string) => api<StudentAlert[]>("/students/me/alerts", {}, token),
  predictions: (token: string) => api<Predictions>("/students/me/predictions", {}, token),
  advise: (courseCode: string, token: string) =>
    api<AdviseResponse>("/students/me/advise", { method: "POST", body: JSON.stringify({ course_code: courseCode }) }, token),
  today: (token: string) => api<TodayPlan>("/students/me/today", {}, token),
  weaknesses: (token: string) => api<Weaknesses>("/students/me/weaknesses", {}, token),
  recommendations: (token: string) => api<Recommendations>("/students/me/recommendations", {}, token),
  careerReadiness: (token: string) => api<CareerReadiness>("/students/me/career-readiness", {}, token),
  studyGroups: (token: string) => api<StudyGroups>("/students/me/study-groups", {}, token),
  notifications: (token: string) => api<NotificationsResponse>("/students/me/notifications", {}, token),
  gamification: (token: string) => api<Gamification>("/students/me/gamification", {}, token),
  digitalTwin: (token: string) => api<DigitalTwin>("/students/me/digital-twin", {}, token),
  progress: (token: string) => api<ProgressAnalytics>("/students/me/progress", {}, token),
  examPrep: (token: string, courseCode: string, count = 5) =>
    api<ExamPrep>(`/students/me/exam-prep?course_code=${encodeURIComponent(courseCode)}&count=${count}`, {}, token),
  assignmentAssist: (token: string, body: { course_code: string; assignment_text: string; ask: string }) =>
    api<AssignmentAssist>("/students/me/assignment-assist", { method: "POST", body: JSON.stringify(body) }, token),
  mockInterview: (token: string, role: string) =>
    api<InterviewQuestion>("/students/me/mock-interview", { method: "POST", body: JSON.stringify({ role }) }, token),
  mockInterviewScore: (token: string, body: { role: string; question: string; answer: string }) =>
    api<InterviewScore>("/students/me/mock-interview/score", { method: "POST", body: JSON.stringify(body) }, token),
  resumeAts: (token: string, resumeText: string) =>
    api<ResumeATS>("/students/me/resume-ats", { method: "POST", body: JSON.stringify({ resume_text: resumeText }) }, token),
  projectMentor: (token: string, body: { project_title: string; project_description: string; question: string }) =>
    api<ProjectMentor>("/students/me/project-mentor", { method: "POST", body: JSON.stringify(body) }, token),
  myTimetable: (token: string) => api<MyTimetable>("/students/me/timetable", {}, token),
  myPlacements: (token: string) => api<MyPlacements>("/students/me/placements", {}, token),
  applyToDrive: (driveId: string, token: string) =>
    api<{ id: string; status: string; message: string }>(
      "/students/me/applications",
      { method: "POST", body: JSON.stringify({ drive_id: driveId }) },
      token
    ),
  withdrawApplication: (driveId: string, token: string) =>
    api<{ id: string; status: string; message: string }>(
      `/students/me/applications/${driveId}`,
      { method: "DELETE" },
      token
    ),
  decideOffer: (selectionId: string, decision: "accepted" | "rejected", token: string) =>
    api<{ id: string; offer_status: string; message: string }>(
      `/students/me/selections/${selectionId}/decide`,
      { method: "POST", body: JSON.stringify({ decision }) },
      token
    ),
  uploadResume: (file: File, token: string) => {
    const form = new FormData();
    form.append("file", file);
    return api<ResumeInfo & { message: string }>(
      "/students/me/resume",
      { method: "POST", body: form },
      token
    );
  },
  getResume: (token: string) => api<ResumeInfo | { message: string }>("/students/me/resume", {}, token),
  deleteResume: (token: string) =>
    api<{ message: string }>("/students/me/resume", { method: "DELETE" }, token),
  askStudyAssistant: (token: string, question: string) =>
    api<StudyAnswer>("/students/me/ask", { method: "POST", body: JSON.stringify({ question }) }, token),
};
