import { type LucideIcon } from "lucide-react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  accent?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ title, subtitle, icon: Icon, accent, actions }: PageHeaderProps) {
  return (
    <div className="fade-up flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        {Icon && (
          <span
            className={`grid h-12 w-12 shrink-0 place-items-center rounded-2xl shadow-sm ${
              accent ?? "bg-[var(--primary)]/10 text-[var(--primary)]"
            }`}
          >
            <Icon className="h-6 w-6" />
          </span>
        )}
        <div>
          <h1 className="text-xl font-bold tracking-tight md:text-2xl">{title}</h1>
          {subtitle && <p className="mt-0.5 text-sm text-[var(--muted-foreground)]">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
