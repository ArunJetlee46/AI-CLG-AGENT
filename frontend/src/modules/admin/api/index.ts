export * from "./ai";
export * from "./analytics";
export * from "./audit";
export * from "./engagement";
export * from "./intelligence";
export * from "./models";
export * from "./resources";
export * from "./system";
export * from "./users";

import { aiApi } from "./ai";
import { analyticsApi } from "./analytics";
import { auditApi } from "./audit";
import { engagementApi } from "./engagement";
import { intelligenceApi } from "./intelligence";
import { modelsApi } from "./models";
import { resourcesApi } from "./resources";
import { systemApi } from "./system";
import { usersApi } from "./users";

export const adminApi = {
  ...intelligenceApi,
  ...usersApi,
  ...resourcesApi,
  ...modelsApi,
  ...engagementApi,
  ...analyticsApi,
  ...systemApi,
  ...auditApi,
  ...aiApi,
};
