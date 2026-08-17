import { type ModuleRoute } from "@/core/lib/routes";

import { AnalyticsDashboard } from "./AnalyticsDashboard";
import { Chat } from "./Chat";
import { AgentTracePanel } from "@/modules/shared/AgentTracePanel";

export const moduleRoutes: ModuleRoute[] = [
  { path: "/chat", element: <Chat /> },
  { path: "/analytics", element: <AnalyticsDashboard />, roles: ["lecturer", "admin"] },
  { path: "/agent-trace", element: <AgentTracePanel />, roles: ["admin", "lecturer"] },
];
