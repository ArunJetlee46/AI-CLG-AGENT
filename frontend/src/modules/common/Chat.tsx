import { Bot, Check, Copy, Send, Sparkles } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { chatStream } from "@/core/lib/api";
import { cn } from "@/core/lib/utils";
import { useAuthStore } from "@/core/stores/auth";

interface Message {
  role: "user" | "assistant";
  content: string;
  meta?: string;
  error?: boolean;
}

const SUGGESTIONS = [
  "Which students are at risk of dropout?",
  "What courses does Computer Science offer?",
  "Explain the timetable optimization",
  "What is the university placement rate?",
];

export function Chat() {
  const token = useAuthStore((s) => s.token);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hello! I'm the Beru Campus AI assistant. Ask about courses, registration, risk prediction, timetables, or run knowledge-graph queries. I'm a propose-only agent — nothing I do writes to the system without an approval.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [searchParams] = useSearchParams();

  async function copyMessage(index: number) {
    const message = messages[index];
    if (!message) return;
    try {
      await navigator.clipboard.writeText(message.content + (message.meta ? `\n\n[${message.meta}]` : ""));
      setCopied(index);
      setTimeout(() => setCopied((c) => (c === index ? null : c)), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }

  useEffect(() => {
    const prompt = searchParams.get("q");
    if (prompt) setInput(prompt);
  }, [searchParams]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function send(event: FormEvent, preset?: string) {
    event.preventDefault();
    const question = (preset ?? input).trim();
    if (!question || !token) return;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);
    const assistantIndexRef = { current: 0 };
    setMessages((prev) => {
      assistantIndexRef.current = prev.length;
      return [...prev, { role: "user", content: question }, { role: "assistant", content: "" }];
    });
    let metaChips = "";

    const patchAnswer = (delta: string) =>
      setMessages((prev) =>
        prev.map((message, i) =>
          i === assistantIndexRef.current ? { ...message, content: message.content + delta } : message
        )
      );

    try {
      await chatStream(
        question,
        token,
        (text) => {
          setMessages((prev) => {
            const copy = [...prev];
            const last = copy[copy.length - 1];
            if (last.role === "assistant" && !last.error) {
              copy[copy.length - 1] = { ...last, content: last.content + text };
            }
            return copy;
          });
        },
        (final) => {
          const via = final.provider
            ? ` via ${final.provider === "local-fallback" ? "local fallback" : final.provider}${final.model ? ` (${final.model})` : ""}`
            : "";
          const chips = [
            `intent ${final.intent}`,
            final.agent,
            via || undefined,
            final.approval_id ? `approval ${final.approval_id.slice(0, 8)}` : undefined,
            final.decision_card_id ? `card ${final.decision_card_id.slice(0, 8)}` : undefined,
          ].filter(Boolean);
          setMessages((prev) => {
            const copy = [...prev];
            const last = copy[copy.length - 1];
            if (last.role === "assistant" && !last.error) {
              copy[copy.length - 1] = {
                ...last,
                content: final.answer || last.content,
                meta: chips.join(" · "),
              };
            }
            return copy;
          });
        },
        (message) => {
          setMessages((prev) => {
            const copy = [...prev];
            const last = copy[copy.length - 1];
            if (last.role === "assistant") {
              copy[copy.length - 1] = { ...last, content: `Error: ${message}`, meta: "request failed", error: true };
            }
            return copy;
          });
        },
      );
    } catch (err) {
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last.role === "assistant") {
          copy[copy.length - 1] = {
            ...last,
            content: `Error: ${err instanceof Error ? err.message : "request failed"}`,
            meta: "request failed",
            error: true,
          };
        }
        return copy;
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="AI Assistant"
        subtitle="Ask anything about Beru — grounded, approval-gated, and audited"
        icon={Sparkles}
      />

      <Card className="flex h-[calc(100vh-12rem)] min-h-[28rem] flex-col overflow-hidden">
        <div ref={scrollRef} className="flex flex-1 flex-col gap-4 overflow-y-auto p-5">
          {messages.map((message, index) => (
            <div
              key={index}
              className={cn(
                "fade-up flex max-w-[85%] gap-2.5",
                message.role === "user" ? "self-end" : "self-start"
              )}
            >
              {message.role === "assistant" && (
                <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[var(--primary)] text-white">
                  <Bot className="h-4 w-4" />
                </span>
              )}
              <div
                className={cn(
                  "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                  message.role === "user"
                    ? "rounded-br-sm bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm shadow-[var(--primary)]/20"
                    : cn(
                        "rounded-bl-sm border border-[var(--border)] bg-[var(--card)] shadow-sm",
                        message.error && "border-red-300 bg-red-50"
                      )
                )}
              >
                {message.role === "assistant" && message.content && !(busy && index === messages.length - 1) && (
                  <div className="flex justify-end">
                    <button
                      type="button"
                      aria-label="Copy answer"
                      onClick={() => copyMessage(index)}
                      className="mb-1 inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                    >
                      {copied === index ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      {copied === index ? "Copied" : "Copy"}
                    </button>
                  </div>
                )}
                <div className="whitespace-pre-wrap">{message.content}</div>
                {message.meta && !message.error && (
                  <div className="mt-1.5 flex flex-wrap gap-1.5 border-t border-[var(--border)]/60 pt-2">
                    {message.meta.split(" · ").map((chip) => (
                      <span
                        key={chip}
                        className="rounded-full bg-[var(--muted)] px-2 py-0.5 text-[11px] text-[var(--muted-foreground)]"
                      >
                        {chip}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && (
            <div className="fade-up flex items-center gap-2.5 self-start">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-[var(--primary)] text-white">
                <Bot className="h-4 w-4" />
              </span>
              <div className="flex gap-1 rounded-2xl rounded-bl-sm border border-[var(--border)] bg-[var(--card)] px-4 py-3">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-2 w-2 animate-bounce rounded-full bg-[var(--primary)]"
                    style={{ animationDelay: `${i * 120}ms` }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {messages.length <= 1 && (
          <div className="flex flex-wrap gap-2 px-5 pb-3">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={(e) => send(e, suggestion)}
                className="rounded-full border border-[var(--border)] bg-[var(--muted)] px-3 py-1.5 text-xs text-[var(--muted-foreground)] transition-colors hover:border-[var(--primary)] hover:text-[var(--primary)]"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        <form onSubmit={send} className="flex items-center gap-2 border-t border-[var(--border)] bg-[var(--muted)]/40 p-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='Try: "Which students are at risk of dropout?"'
            disabled={busy}
            className="border-transparent bg-white shadow-sm"
          />
          <Button type="submit" disabled={busy || !input.trim()} className="shrink-0">
            {busy ? "Thinking…" : <Send className="h-4 w-4" />}
          </Button>
        </form>
      </Card>
    </div>
  );
}
