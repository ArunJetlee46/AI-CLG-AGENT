import { cn } from "@/core/lib/utils";

export function Progress({
  value,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { value: number }) {
  return (
    <div
      className={cn("relative h-3 w-full overflow-hidden rounded-full bg-[var(--muted)]", className)}
      {...props}
    >
      <div
        className="h-full bg-[var(--primary)] transition-all duration-300 ease-out"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}