import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/core/components/ui/badge";
import { useAuthStore } from "@/core/stores/auth";
import { facultyApi } from "./api";

export function ProviderBadge({ provider }: { provider: string }) {
  return (
    <Badge tone={provider === "llm" ? "success" : "warning"}>
      {provider === "llm" ? "AI generated" : "template"}
    </Badge>
  );
}

export function CourseChips({ value, onChange }: { value: string; onChange: (code: string) => void }) {
  const token = useAuthStore((s) => s.token);
  const profile = useQuery({ queryKey: ["fac-profile"], queryFn: () => facultyApi.me(token!), enabled: !!token });

  if (!profile.data?.courses.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-[var(--muted-foreground)]">Course:</span>
      {profile.data.courses.map((c) => (
        <button
          key={c.course_code}
          onClick={() => onChange(value === c.course_code ? "" : c.course_code)}
          className={`rounded-full border px-3 py-1 text-sm transition-colors ${value === c.course_code ? "border-[var(--primary)] bg-[var(--primary)]/10 font-medium text-[var(--primary)]" : "border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--muted)]"}`}
        >
          {c.course_code}
        </button>
      ))}
    </div>
  );
}
