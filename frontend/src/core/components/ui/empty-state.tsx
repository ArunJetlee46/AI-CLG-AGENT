import { Inbox, type LucideIcon } from "lucide-react";

import { cn } from "@/core/lib/utils";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title = "Nothing here yet",
  description = "Data will appear here once it is available.",
  icon: Icon = Inbox,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-[var(--border)] bg-[var(--muted)]/40 px-6 py-10 text-center",
        className
      )}
    >
      <span className="grid h-11 w-11 place-items-center rounded-full bg-[var(--muted)] text-[var(--muted-foreground)]">
        <Icon className="h-5 w-5" />
      </span>
      <p className="text-sm font-semibold">{title}</p>
      <p className="max-w-sm text-xs text-[var(--muted-foreground)]">{description}</p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
