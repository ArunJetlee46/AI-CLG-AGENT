import { type ModuleRoute } from "@/core/lib/routes";

import { AnalyticsDashboard } from "./AnalyticsDashboard";
import { Chat } from "./Chat";

export const moduleRoutes: ModuleRoute[] = [
  { path: "/chat", element: <Chat /> },
  { path: "/analytics", element: <AnalyticsDashboard />, roles: ["lecturer", "admin"] },
];
