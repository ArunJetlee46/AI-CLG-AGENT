import { Bot, LifeBuoy, Send, X } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { agentApi, type ChatResponse } from "@/core/lib/api";
import { findSiteHelp, HELP_FALLBACK, HELP_TOPICS } from "@/core/lib/site-help";
import { cn } from "@/core/lib/utils";
import { useAuthStore } from "@/core/stores/auth";

interface Message {
  role: "user" | "assistant";
  content: string;
  meta?: string;
  error?: boolean;
}

export function HelpAssistant() {
  const token = useAuthStore((s) => s.token);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hi! I'm the Beru site assistant. Ask me anything about this website — how to use it, what each role can do, where to find things, or how approvals and the audit trail work.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy, open]);

  async function send(event: FormEvent, preset?: string) {
    event.preventDefault();
    const question = (preset ?? input).trim();
    if (!question || busy) return;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setBusy(true);
    try {
      const local = findSiteHelp(question);
      if (local) {
        setMessages((prev) => [...prev, { role: "assistant", content: local.answer, meta: "site help" }]);
        return;
      }
      if (!token) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: HELP_FALLBACK, meta: "site help" },
        ]);
        return;
      }
      const response: ChatResponse = await agentApi.chat(question, token);
      const via = response.provider
        ? ` via ${response.provider === "local-fallback" ? "local fallback" : response.provider} (${response.model})`
        : "";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer, meta: `main AI assistant${via}` },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry, I couldn't get an answer: ${err instanceof Error ? err.message : "request failed"}. Try again or ask about this website — I have offline help for navigation, roles and features.`,
          meta: "request failed",
          error: true,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        aria-label="Ask the site assistant"
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "fixed bottom-5 right-5 z-[70] inline-flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition-transform hover:scale-105 active:scale-95",
          "bg-gradient-to-br from-[var(--primary)] to-violet-500 text-white",
          open && "scale-95"
        )}
      >
        {open ? <X className="h-6 w-6" /> : <LifeBuoy className="h-6 w-6" />}
      </button>

      {open && (
        <div className="fade-up fixed bottom-24 right-5 z-[70] flex h-[32rem] w-[min(22rem,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-2xl">
          <div className="flex items-center gap-2.5 border-b border-[var(--border)] bg-[var(--muted)]/50 px-4 py-3">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[var(--primary)] text-white">
              <Bot className="h-4 w-4" />
            </span>
            <div className="min-w-0 leading-tight">
              <p className="truncate text-sm font-semibold">Site Assistant</p>
              <p className="truncate text-[11px] text-[var(--muted-foreground)]">
                How to use this website — instant answers
              </p>
            </div>
          </div>

          <div ref={scrollRef} className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={cn(
                  "flex max-w-[90%] gap-2",
                  message.role === "user" ? "self-end" : "self-start"
                )}
              >
                {message.role === "assistant" && (
                  <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[var(--primary)] text-white">
                    <Bot className="h-3.5 w-3.5" />
                  </span>
                )}
                <div
                  className={cn(
                    "whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-[13px] leading-relaxed",
                    message.role === "user"
                      ? "rounded-br-sm bg-[var(--primary)] text-[var(--primary-foreground)]"
                      : cn(
                          "rounded-bl-sm border border-[var(--border)] bg-[var(--card)]",
                          message.error && "border-red-300 bg-red-50"
                        )
                  )}
                >
                  {message.content}
                  {message.meta && !message.error && (
                    <div className="mt-1.5 border-t border-[var(--border)]/60 pt-1.5 text-[10px] text-[var(--muted-foreground)]">
                      {message.meta}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex gap-1 self-start rounded-2xl rounded-bl-sm border border-[var(--border)] bg-[var(--card)] px-4 py-3">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--primary)]"
                    style={{ animationDelay: `${i * 120}ms` }}
                  />
                ))}
              </div>
            )}
          </div>

          {messages.length <= 1 && (
            <div className="flex flex-wrap gap-1.5 px-4 pb-2">
              {HELP_TOPICS.map((topic) => (
                <button
                  key={topic}
                  type="button"
                  onClick={(e) => send(e, topic)}
                  className="rounded-full border border-[var(--border)] bg-[var(--muted)] px-2.5 py-1 text-[11px] text-[var(--muted-foreground)] transition-colors hover:border-[var(--primary)] hover:text-[var(--primary)]"
                >
                  {topic}
                </button>
              ))}
            </div>
          )}

          <form
            onSubmit={send}
            className="flex items-center gap-2 border-t border-[var(--border)] bg-[var(--muted)]/40 p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder='Try: "How do approvals work?"'
              disabled={busy}
              className="h-9 w-full rounded-md border border-[var(--border)] bg-white px-3 text-sm placeholder:text-[var(--muted-foreground)] focus:border-[var(--primary)]/40 focus:outline-none"
            />
            <button
              type="submit"
              aria-label="Send"
              disabled={busy || !input.trim()}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-[var(--primary)] text-white transition-colors hover:brightness-110 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
