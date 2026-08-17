import { type ModuleRoute } from "@/core/lib/routes";

import { Announcements } from "@/modules/common/Announcements";
import { Companies } from "./Companies";
import { CsvImport } from "./CsvImport";
import { Drives } from "./Drives";
import { GapAnalysis } from "./GapAnalysis";
import { JDAnalyzer } from "./JDAnalyzer";
import { Matching } from "./Matching";
import { Notifications } from "./Notifications";
import { PlacementAnalytics } from "./PlacementAnalytics";
import { PlacementDashboard } from "./PlacementDashboard";
import { PlacementFlow } from "./PlacementFlow";
import { PlacementLanding } from "./PlacementLanding";
import { Reports } from "./Reports";

export const moduleRoutes: ModuleRoute[] = [
  { path: "/placement", element: <PlacementLanding />, roles: ["placement", "admin"] },
  { path: "/placement/flow", element: <PlacementFlow />, roles: ["placement", "admin"] },
  { path: "/placement/dashboard", element: <PlacementDashboard />, roles: ["placement", "admin"] },
  { path: "/placement/jd", element: <JDAnalyzer />, roles: ["placement", "admin"] },
  { path: "/placement/matching", element: <Matching />, roles: ["placement", "admin"] },
  { path: "/placement/drives", element: <Drives />, roles: ["placement", "admin"] },
  { path: "/placement/import", element: <CsvImport />, roles: ["placement", "admin"] },
  { path: "/placement/analytics", element: <PlacementAnalytics />, roles: ["placement", "admin"] },
  { path: "/placement/gaps", element: <GapAnalysis />, roles: ["placement", "admin"] },
  { path: "/placement/companies", element: <Companies />, roles: ["placement", "admin"] },
  { path: "/placement/notifications", element: <Notifications />, roles: ["placement", "admin"] },
  { path: "/placement/announcements", element: <Announcements />, roles: ["placement", "admin"] },
  { path: "/placement/reports", element: <Reports />, roles: ["placement", "admin"] },
];
