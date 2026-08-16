import { type ModuleRoute } from "@/core/lib/routes";

import { Announcements } from "@/modules/common/Announcements";
import { AdminDashboard } from "./AdminDashboard";
import { AdminAccreditation } from "./pages/analytics/Accreditation";
import { AdminApprovals } from "./pages/operations/ApprovalsCenter";
import { AdminAuditCenter } from "./pages/operations/AuditCenter";
import { AdminBackups } from "./pages/operations/Backups";
import { AdminCopilot } from "./pages/ai/Copilot";
import { AdminCurriculumIntelligence } from "./pages/analytics/CurriculumIntelligence";
import { AdminDepartments } from "./pages/operations/Departments";
import { AdminDigitalTwin } from "./pages/ai/DigitalTwin";
import { AdminDropoutAnalytics } from "./pages/analytics/DropoutAnalytics";
import { AdminEnrollmentForecast } from "./pages/analytics/EnrollmentForecast";
import { AdminEvaluationCenter } from "./pages/ai/EvaluationCenter";
import { AdminFacultyAnalytics } from "./pages/analytics/FacultyAnalytics";
import { AdminGovernance } from "./pages/operations/Governance";
import { AdminIndustry } from "./pages/engagement/Industry";
import { AdminModelRegistry } from "./pages/operations/ModelRegistry";
import { AdminPlacementAnalytics } from "./pages/analytics/PlacementAnalytics";
import { AdminResearch } from "./pages/engagement/Research";
import { AdminResources } from "./pages/operations/Resources";
import { AdminStudentAnalytics } from "./pages/analytics/StudentAnalytics";
import { AdminSystemHealth } from "./pages/operations/SystemHealth";
import { AdminTimetable } from "./pages/operations/Timetable";
import { AdminUsers } from "./pages/operations/Users";

export const moduleRoutes: ModuleRoute[] = [
  { path: "/admin", element: <AdminDashboard />, roles: ["admin"] },
  { path: "/admin/users", element: <AdminUsers />, roles: ["admin"] },
  { path: "/admin/departments", element: <AdminDepartments />, roles: ["admin"] },
  { path: "/admin/announcements", element: <Announcements />, roles: ["admin"] },
  { path: "/admin/resources", element: <AdminResources />, roles: ["admin"] },
  { path: "/admin/backups", element: <AdminBackups />, roles: ["admin"] },
  { path: "/admin/models", element: <AdminModelRegistry />, roles: ["admin"] },
  { path: "/admin/analytics/students", element: <AdminStudentAnalytics />, roles: ["admin"] },
  { path: "/admin/analytics/faculty", element: <AdminFacultyAnalytics />, roles: ["admin"] },
  { path: "/admin/analytics/placement", element: <AdminPlacementAnalytics />, roles: ["admin"] },
  { path: "/admin/analytics/dropout", element: <AdminDropoutAnalytics />, roles: ["admin"] },
  { path: "/admin/analytics/curriculum", element: <AdminCurriculumIntelligence />, roles: ["admin"] },
  { path: "/admin/analytics/enrollment-forecast", element: <AdminEnrollmentForecast />, roles: ["admin"] },
  { path: "/admin/analytics/accreditation", element: <AdminAccreditation />, roles: ["admin"] },
  { path: "/admin/research", element: <AdminResearch />, roles: ["admin"] },
  { path: "/admin/industry", element: <AdminIndustry />, roles: ["admin"] },
  { path: "/admin/approvals", element: <AdminApprovals />, roles: ["admin"] },
  { path: "/admin/audit", element: <AdminAuditCenter />, roles: ["admin"] },
  { path: "/admin/governance", element: <AdminGovernance />, roles: ["admin"] },
  { path: "/admin/system-health", element: <AdminSystemHealth />, roles: ["admin"] },
  { path: "/admin/copilot", element: <AdminCopilot />, roles: ["admin"] },
  { path: "/admin/digital-twin", element: <AdminDigitalTwin />, roles: ["admin"] },
  { path: "/admin/timetable", element: <AdminTimetable />, roles: ["admin"] },
  { path: "/admin/evaluation", element: <AdminEvaluationCenter />, roles: ["admin"] },
  { path: "/admin/agent-plugins", element: <AgentPluginManager />, roles: ["admin"] },
];
