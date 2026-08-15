import { Navigate } from "react-router-dom";

import { useAuthStore } from "@/core/stores/auth";

const HOME_BY_ROLE: Record<string, string> = {
  student: "/student",
  lecturer: "/faculty",
  placement: "/placement",
  admin: "/admin",
};

export function RoleHome() {
  const role = useAuthStore((s) => s.role);
  if (!role) return <Navigate to="/login" replace />;
  return <Navigate to={HOME_BY_ROLE[role] ?? "/student"} replace />;
}
