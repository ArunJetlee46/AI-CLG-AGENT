import type { ReactNode } from "react";

export interface ModuleRoute {
  path: string;
  element: ReactNode;
  roles?: string[];
}
