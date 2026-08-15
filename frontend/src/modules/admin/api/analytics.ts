import { api } from "@/core/lib/api";

import type { AdminCommandCenter, FacultyWorkloadRow } from "./intelligence";

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

export const analyticsApi = {
  studentAnalytics: (token: string) => api<StudentAnalytics>("/admin/analytics/students", {}, token),
  facultyAnalytics: (token: string) => api<FacultyAnalytics>("/admin/analytics/faculty", {}, token),
  placementAnalytics: (token: string) => api<PlacementOverview>("/admin/analytics/placement", {}, token),
  kpis: (token: string) => api<AdminCommandCenter & { university_health_score: number; axes: Record<string, number>; basis: Record<string, number | null> }>("/admin/analytics/kpis", {}, token),
  dropoutAnalytics: (token: string) => api<DropoutAnalytics>("/admin/analytics/dropout", {}, token),
  curriculum: (token: string) => api<CurriculumReport>("/admin/analytics/curriculum", {}, token),
  enrollmentForecast: (token: string) => api<EnrollmentForecast>("/admin/analytics/enrollment-forecast", {}, token),
  accreditation: (token: string) => api<AccreditationReport>("/admin/analytics/accreditation", {}, token),
};
