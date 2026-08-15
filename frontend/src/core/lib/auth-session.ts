import { toast } from "@/core/components/ui/toast";
import { useAuthStore } from "@/core/stores/auth";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

/** Refresh when the access token is within this many ms of expiring. */
export const PROACTIVE_THRESHOLD_MS = 60_000;

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

let inFlight: Promise<string> | null = null;
let refreshTimer: ReturnType<typeof setTimeout> | null = null;

/** Clears both access + refresh tokens locally and bounces to /login. */
export function clearSession(reason: string): void {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
  const { logout } = useAuthStore.getState();
  logout();
  toast.error("Session expired", reason);
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.assign(`/login?expired=1`);
  }
}

/**
 * Rotates the token pair via /auth/refresh.
 * Single-flight: concurrent callers share the same in-flight request.
 * Returns the new access token.
 */
export async function refreshAccessToken(): Promise<string> {
  const { refreshToken } = useAuthStore.getState();
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }
  if (inFlight) return inFlight;

  inFlight = (async () => {
    const response = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      let detail = "Refresh token is invalid or expired";
      try {
        const body = await response.json();
        if (typeof body?.detail === "string") detail = body.detail;
      } catch {
        /* ignore */
      }
      clearSession(detail);
      throw new Error(detail);
    }
    const pair = (await response.json()) as TokenPair;
    const { setTokens } = useAuthStore.getState();
    setTokens(pair.access_token, pair.refresh_token);
    scheduleProactiveRefresh();
    return pair.access_token;
  })();

  try {
    return await inFlight;
  } finally {
    inFlight = null;
  }
}

/** Refreshes proactively if the access token is missing or close to expiry. */
export async function ensureFreshToken(): Promise<void> {
  const { token, refreshToken, expiresAt } = useAuthStore.getState();
  if (!token || !refreshToken) return;
  if (expiresAt === null) return;
  if (expiresAt - Date.now() > PROACTIVE_THRESHOLD_MS) return;
  await refreshAccessToken();
}

/** Schedules a silent refresh just before the access token expires. */
export function scheduleProactiveRefresh(): void {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
  const { expiresAt } = useAuthStore.getState();
  if (typeof expiresAt !== "number") return;
  const delay = expiresAt - Date.now() - PROACTIVE_THRESHOLD_MS;
  if (delay <= 0) {
    void refreshAccessToken().catch(() => {});
    return;
  }
  refreshTimer = setTimeout(() => {
    void refreshAccessToken().catch(() => {});
  }, delay);
}
