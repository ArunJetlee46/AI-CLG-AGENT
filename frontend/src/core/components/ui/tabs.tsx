"use client";

import * as React from "react";
import { cn } from "@/core/lib/utils";

interface TabsContextValue {
  value: string;
  onValueChange: (value: string) => void;
}

const TabsContext = React.createContext<TabsContextValue | null>(null);

function useTabsContext() {
  const context = React.useContext(TabsContext);
  if (!context) {
    throw new Error("Tabs components must be used within Tabs");
  }
  return context;
}

export function Tabs({
  value,
  onValueChange,
  children,
  className,
  defaultValue,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  value?: string;
  onValueChange?: (value: string) => void;
  defaultValue?: string;
}) {
  const [internalValue, setInternalValue] = React.useState(defaultValue ?? "");
  const controlled = value !== undefined;
  const currentValue = controlled ? value : internalValue;

  const handleValueChange = React.useCallback(
    (val: string) => {
      if (!controlled) setInternalValue(val);
      onValueChange?.(val);
    },
    [controlled, onValueChange]
  );

  return (
    <TabsContext.Provider value={{ value: currentValue ?? "", onValueChange: handleValueChange }}>
      <div className={cn("flex flex-col gap-4", className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

export function TabsList({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("inline-flex h-9 items-center justify-center rounded-md bg-[var(--muted)] p-1 text-[var(--muted-foreground)]", className)}
      role="tablist"
      {...props}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({
  value,
  children,
  className,
  disabled,
  ...props
}: React.HTMLAttributes<HTMLButtonElement> & { value: string; disabled?: boolean }) {
  const { value: contextValue, onValueChange } = useTabsContext();
  const isActive = contextValue === value;

  return (
    <button
      role="tab"
      aria-selected={isActive}
      disabled={disabled}
      onClick={() => !disabled && onValueChange(value)}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        isActive
          ? "bg-[var(--card)] text-[var(--foreground)] shadow-sm"
          : "hover:bg-[var(--muted)]/80 hover:text-[var(--foreground)]",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function TabsContent({
  value,
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { value: string }) {
  const { value: contextValue } = useTabsContext();
  const isActive = contextValue === value;

  if (!isActive) return null;

  return (
    <div
      role="tabpanel"
      className={cn("mt-2 ring-offset-[var(--card)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2", className)}
      {...props}
    >
      {children}
    </div>
  );
}