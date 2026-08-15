import { api } from "@/core/lib/api";

import type { AdminCounts, AdminKpis, EarlyWarning, HealthScore } from "./intelligence";

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

export const aiApi = {
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
