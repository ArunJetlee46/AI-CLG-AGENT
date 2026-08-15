import { type ModuleRoute } from "@/core/lib/routes";

import { Announcements } from "@/modules/common/Announcements";
import { AssignmentEval } from "./AssignmentEval";
import { CodeReview } from "./CodeReview";
import { CourseReports } from "./CourseReports";
import { FacultyAudit } from "./FacultyAudit";
import { FacultyCopilot } from "./FacultyCopilot";
import { FacultyDashboard } from "./FacultyDashboard";
import { FacultyIntelligence } from "./FacultyIntelligence";
import { FacultyLanding } from "./FacultyLanding";
import { FacultyTools } from "./FacultyTools";
import { LabAssistant } from "./LabAssistant";
import { LessonPlan } from "./LessonPlan";
import { QuestionPaper } from "./QuestionPaper";
import { Remedial } from "./Remedial";
import { Similarity } from "./Similarity";
import { TeachingMaterial } from "./TeachingMaterial";
import { VivaQuestions } from "./VivaQuestions";

export const moduleRoutes: ModuleRoute[] = [
  { path: "/faculty", element: <FacultyLanding />, roles: ["lecturer", "admin"] },
  { path: "/faculty/copilot", element: <FacultyCopilot />, roles: ["lecturer", "admin"] },
  { path: "/faculty/dashboard", element: <FacultyDashboard />, roles: ["lecturer", "admin"] },
  { path: "/faculty/audit", element: <FacultyAudit />, roles: ["lecturer", "admin"] },
  { path: "/faculty/intelligence", element: <FacultyIntelligence />, roles: ["lecturer", "admin"] },
  { path: "/faculty/course-reports", element: <CourseReports />, roles: ["lecturer", "admin"] },
  { path: "/faculty/similarity", element: <Similarity />, roles: ["lecturer", "admin"] },
  { path: "/faculty/remedial", element: <Remedial />, roles: ["lecturer", "admin"] },
  { path: "/faculty/announcements", element: <Announcements />, roles: ["lecturer", "admin"] },
  { path: "/faculty/tools", element: <FacultyTools />, roles: ["lecturer", "admin"] },
  { path: "/faculty/tools/question-paper", element: <QuestionPaper />, roles: ["lecturer", "admin"] },
  { path: "/faculty/tools/lesson-plan", element: <LessonPlan />, roles: ["lecturer", "admin"] },
  { path: "/faculty/tools/teaching-material", element: <TeachingMaterial />, roles: ["lecturer", "admin"] },
  { path: "/faculty/tools/assignment-eval", element: <AssignmentEval />, roles: ["lecturer", "admin"] },
  { path: "/faculty/tools/code-review", element: <CodeReview />, roles: ["lecturer", "admin"] },
  { path: "/faculty/tools/lab-assistant", element: <LabAssistant />, roles: ["lecturer", "admin"] },
  { path: "/faculty/tools/viva-questions", element: <VivaQuestions />, roles: ["lecturer", "admin"] },
];
