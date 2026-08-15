import { type LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/core/components/ui/card";
import { cn } from "@/core/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number | null | undefined;
  sub?: string;
  icon: LucideIcon;
  /** Tailwind classes for the icon tile (e.g. "bg-sky-100 text-sky-600"). */
  accent?: string;
  /** Optional trend line under the value (e.g. "+3 vs last term"). */
  trend?: string;
  trendTone?: "up" | "down" | "neutral";
}

const trendStyles = {
  up: "text-emerald-600",
  down: "text-red-600",
  neutral: "text-[var(--muted-foreground)]",
};

export function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent = "bg-[var(--primary)]/10 text-[var(--primary)]",
  trend,
  trendTone = "neutral",
}: StatCardProps) {
  return (
    <Card className="card-lift fade-up">
      <CardContent className="flex items-start justify-between gap-3 pt-5">
        <div className="min-w-0">
          <p className="truncate text-sm text-[var(--muted-foreground)]">{label}</p>
          <p className="mt-1 text-2xl font-bold tracking-tight text-[var(--card-foreground)]">{value ?? "—"}</p>
          {trend && <p className={cn("mt-0.5 truncate text-xs font-medium", trendStyles[trendTone])}>{trend}</p>}
          {sub && !trend && <p className="mt-0.5 truncate text-xs text-[var(--muted-foreground)]">{sub}</p>}
        </div>
        <span
          className={cn(
            "grid h-10 w-10 shrink-0 place-items-center rounded-xl shadow-sm transition-transform duration-200 group-hover:scale-110",
            accent
          )}
        >
          <Icon className="h-5 w-5" />
        </span>
      </CardContent>
    </Card>
  );
}
