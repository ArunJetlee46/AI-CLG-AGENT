import { cn } from "@/core/lib/utils";

const badgeVariants: Record<string, string> = {
  neutral: "bg-[var(--muted)] text-[var(--muted-foreground)]",
  primary: "bg-[var(--primary)] text-[var(--primary-foreground)]",
  success: "bg-emerald-600 text-white",
  warning: "bg-yellow-500 text-black",
  destructive: "bg-red-600 text-white",
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof badgeVariants }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        badgeVariants[tone],
        className
      )}
      {...props}
    />
  );
}
