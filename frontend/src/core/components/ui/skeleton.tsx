import { cn } from "@/core/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("skeleton", className)} {...props} />;
}

export function StatCardSkeleton() {
  return (
    <div className="card-shell fade-up flex items-start justify-between gap-3 p-5">
      <div className="min-w-0 flex-1">
        <Skeleton className="h-3.5 w-24" />
        <Skeleton className="mt-2 h-7 w-16" />
        <Skeleton className="mt-1.5 h-3 w-32" />
      </div>
      <Skeleton className="h-10 w-10 shrink-0 rounded-xl" />
    </div>
  );
}
