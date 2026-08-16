import { TriangleAlert, type LucideIcon } from "lucide-react";

import { Button } from "@/core/components/ui/button";
import { cn } from "@/core/lib/utils";

interface ErrorStateProps {
  title?: string;
  description?: string;
  icon?: LucideIcon;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description = "We could not load this data. Please try again.",
  icon: Icon = TriangleAlert,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-[var(--destructive)]/40 bg-[var(--destructive)]/5 px-6 py-10 text-center",
        className
      )}
    >
      <span className="grid h-11 w-11 place-items-center rounded-full bg-[var(--destructive)]/10 text-[var(--destructive)]">
        <Icon className="h-5 w-5" />
      </span>
      <p className="text-sm font-semibold">{title}</p>
      <p className="max-w-sm text-xs text-[var(--muted-foreground)]">{description}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-2" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
