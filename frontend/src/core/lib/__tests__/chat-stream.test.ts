import { afterEach, describe, expect, it, vi } from "vitest";

import { chatStream, type ChatResponse } from "@/core/lib/api";

function sseResponse(frames: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const frame of frames) {
        controller.enqueue(encoder.encode(`${frame}\n\n`));
      }
      controller.close();
    },
  });
  return new Response(stream, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("chatStream", () => {
  it("streams chunks and emits the final done payload", async () => {
    globalThis.fetch = vi.fn(async () =>
      sseResponse([
        'data: {"type":"chunk","content":"Hello "}',
        'data: {"type":"chunk","content":"world"}',
        'data: {"type":"done","intent":"academic","agent":"rag","answer":"Hello world","citations":["CS101"],"requires_approval":false,"approval_id":null,"decision_card_id":null,"provider":"groq","model":"llama-3.3-70b"}',
      ])
    ) as unknown as typeof fetch;

    const chunks: string[] = [];
    const finals: ChatResponse[] = [];
    await chatStream("hello", "token", (t) => chunks.push(t), (f) => finals.push(f), vi.fn());

    const done = finals[0];
    expect(chunks).toEqual(["Hello ", "world"]);
    expect(done?.answer).toBe("Hello world");
    expect(done?.intent).toBe("academic");
    expect(done?.provider).toBe("groq");
    expect(done?.citations).toContain("CS101");

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    expect(call[0]).toMatch(/\/agents\/chat$/);
    expect((call[1].headers as Record<string, string>).Authorization).toBe("Bearer token");
  });

  it("handles an error frame from the stream", async () => {
    globalThis.fetch = vi.fn(async () => sseResponse(['data: {"type":"error","message":"LLM timeout"}'])) as unknown as typeof fetch;

    const onError = vi.fn();
    await chatStream("hello", "token", vi.fn(), vi.fn(), onError);
    expect(onError).toHaveBeenCalledWith("LLM timeout");
  });

  it("rejects with the API detail on a non-ok response", async () => {
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify({ detail: "bad request" }), { status: 400 })) as unknown as typeof fetch;

    await expect(chatStream("x", "token", vi.fn(), vi.fn(), vi.fn())).rejects.toThrow("bad request");
  });
});
