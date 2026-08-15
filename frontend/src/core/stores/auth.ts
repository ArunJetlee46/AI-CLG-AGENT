import { create } from "zustand";
import { persist } from "zustand/middleware";

import { decodeJwt } from "@/core/lib/jwt";

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  role: string | null;
  username: string | null;
  /** Epoch ms at which the current access token expires (null when unknown). */
  expiresAt: number | null;
  setAuth: (token: string, role: string, username: string, refreshToken: string | null) => void;
  setTokens: (token: string, refreshToken: string | null) => void;
  logout: () => void;
}

function tokenExpiry(token: string | null): number | null {
  if (!token) return null;
  const exp = decodeJwt(token).exp;
  return typeof exp === "number" ? exp * 1000 : null;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      role: null,
      username: null,
      expiresAt: null,
      setAuth: (token, role, username, refreshToken) =>
        set({ token, refreshToken, role, username, expiresAt: tokenExpiry(token) }),
      setTokens: (token, refreshToken) => set({ token, refreshToken, expiresAt: tokenExpiry(token) }),
      logout: () => set({ token: null, refreshToken: null, role: null, username: null, expiresAt: null }),
    }),
    { name: "beru-auth" }
  )
);
