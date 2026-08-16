import { type ModuleRoute } from "@/core/lib/routes";

import { AssignmentAssistant } from "./AssignmentAssistant";
import { Community } from "./Community";
import { DegreeAudit } from "./DegreeAudit";
import { ExamPrep } from "./ExamPrep";
import { Insights } from "./Insights";
import { MockInterview } from "./MockInterview";
import { ProjectMentor } from "./ProjectMentor";
import { ResumeATS } from "./ResumeATS";
import { StudentDashboard } from "./StudentDashboard";
import { StudentLanding } from "./StudentLanding";

export const moduleRoutes: ModuleRoute[] = [
  { path: "/student", element: <StudentLanding />, roles: ["student"] },
  { path: "/student/dashboard", element: <StudentDashboard />, roles: ["student"] },
  { path: "/student/insights", element: <Insights />, roles: ["student"] },
  { path: "/student/community", element: <Community />, roles: ["student"] },
  { path: "/student/exam-prep", element: <ExamPrep />, roles: ["student"] },
  { path: "/student/assignment-assistant", element: <AssignmentAssistant />, roles: ["student"] },
  { path: "/student/mock-interview", element: <MockInterview />, roles: ["student"] },
  { path: "/student/resume-ats", element: <ResumeATS />, roles: ["student"] },
  { path: "/student/project-mentor", element: <ProjectMentor />, roles: ["student"] },
  { path: "/student/degree-audit", element: <DegreeAudit />, roles: ["student"] },
];
