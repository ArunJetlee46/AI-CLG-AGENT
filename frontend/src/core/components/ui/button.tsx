import { Loader2 } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/core/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
  {
    variants: {
      variant: {
        default: "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm shadow-[var(--primary)]/30 hover:brightness-110",
        outline: "border border-[var(--border)] bg-transparent hover:bg-[var(--muted)]",
        destructive: "bg-[var(--destructive)] text-white shadow-sm shadow-[var(--destructive)]/30 hover:brightness-110",
        ghost: "hover:bg-[var(--muted)]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-11 px-6",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Shows an inline spinner and disables the button while truthy. */
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, disabled, type = "button", children, ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  )
);
Button.displayName = "Button";

export { Button, buttonVariants };
