import { Check, Copy, Download } from "lucide-react";
import { useCallback, useState } from "react";
import { cn } from "@/core/lib/utils";

interface ToolExportBarProps {
  data: unknown;
  label: string;
  className?: string;
}

function toMarkdown(data: unknown): string {
  if (typeof data === "string") return data;
  if (Array.isArray(data)) {
    return data
      .map((item) => {
        if (typeof item === "string") return `- ${item}`;
        if (typeof item === "object" && item !== null) {
          return Object.entries(item as Record<string, unknown>)
            .map(([k, v]) => `**${k}**: ${v}`)
            .join("\n");
        }
        return String(item);
      })
      .join("\n\n");
  }
  if (typeof data === "object" && data !== null) {
    return Object.entries(data as Record<string, unknown>)
      .map(([k, v]) => `## ${k}\n\n${typeof v === "string" ? v : JSON.stringify(v, null, 2)}`)
      .join("\n\n");
  }
  return String(data);
}

function downloadFile(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function ToolExportBar({ data, label, className }: ToolExportBarProps) {
  const [copied, setCopied] = useState(false);

  const md = toMarkdown(data);
  const filename = label.toLowerCase().replace(/\s+/g, "_") + ".md";

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(md);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }, [md]);

  return (
    <div className={cn("flex items-center gap-2 border-t border-[var(--border)]/60 pt-3 mt-3", className)}>
      <button
        type="button"
        onClick={copy}
        className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--muted)] px-2.5 py-1 text-xs text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)]/80 hover:text-[var(--foreground)]"
      >
        {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        {copied ? "Copied" : "Copy as Markdown"}
      </button>
      <button
        type="button"
        onClick={() => downloadFile(md, filename)}
        className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--muted)] px-2.5 py-1 text-xs text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)]/80 hover:text-[var(--foreground)]"
      >
        <Download className="h-3 w-3" />
        Download .md
      </button>
    </div>
  );
}
