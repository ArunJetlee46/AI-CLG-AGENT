import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuthStore } from "@/core/stores/auth";

interface ProtectedRouteProps {
  roles?: string[];
  children: ReactNode;
}

/** Role-gated route: requires a valid token and (optionally) a role. */
export function ProtectedRoute({ roles, children }: ProtectedRouteProps) {
  const token = useAuthStore((s) => s.token);
  const role = useAuthStore((s) => s.role);

  if (!token) return <Navigate to="/login" replace />;
  if (roles && role && !roles.includes(role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}
