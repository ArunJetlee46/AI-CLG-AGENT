import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/core/lib/api";
import { useAuthStore } from "@/core/stores/auth";

const NEW_ACCESS = "new-access-token";
const NEW_REFRESH = "refresh-token-2";

function makeJwt(expSeconds: number): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(JSON.stringify({ sub: "u1", role: "student", type: "access", exp: expSeconds }));
  return `${header}.${payload}.sig`;
}

describe("concurrent 401 refresh", () => {
  let refreshCalls: string[];
  let originalCalls: number;

  beforeEach(() => {
    refreshCalls = [];
    originalCalls = 0;
    useAuthStore.setState({
      token: makeJwt(Math.floor(Date.now() / 1000) + 600),
      refreshToken: "refresh-token-1",
      role: "student",
      username: "stu",
      expiresAt: Date.now() + 600_000,
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/auth/refresh")) {
          refreshCalls.push(url);
          return new Response(
            JSON.stringify({ access_token: NEW_ACCESS, refresh_token: NEW_REFRESH }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          );
        }
        originalCalls += 1;
        const authHeader = (init?.headers as Record<string, string> | undefined)?.Authorization ?? "";
        if (authHeader === `Bearer ${NEW_ACCESS}`) {
          return new Response(JSON.stringify({ ok: true, token: authHeader }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        return new Response(JSON.stringify({ detail: "expired" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        });
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    useAuthStore.getState().logout();
  });

  it("4 concurrent expired-token requests trigger exactly 1 refresh and all retries succeed", async () => {
    const results = await Promise.all([
      api("/foo/1", {}, "stale-access-token"),
      api("/foo/2", {}, "stale-access-token"),
      api("/foo/3", {}, "stale-access-token"),
      api("/foo/4", {}, "stale-access-token"),
    ]);

    expect(refreshCalls).toHaveLength(1);
    expect(originalCalls).toBe(8);
    results.forEach((r) => expect(r).toEqual({ ok: true, token: `Bearer ${NEW_ACCESS}` }));

    const state = useAuthStore.getState();
    expect(state.token).toBe(NEW_ACCESS);
    expect(state.refreshToken).toBe(NEW_REFRESH);
  });
});
