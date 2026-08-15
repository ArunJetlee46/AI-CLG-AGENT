import { AlertTriangle, CheckCircle2, Info, XCircle, X } from "lucide-react";
import { create } from "zustand";

export type ToastTone = "success" | "error" | "info" | "warning";

interface Toast {
  id: number;
  title: string;
  description?: string;
  tone: ToastTone;
}

interface ToastStore {
  toasts: Toast[];
  push: (toast: Omit<Toast, "id">) => void;
  dismiss: (id: number) => void;
}

let nextId = 0;

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  push: (toast) => {
    const id = ++nextId;
    set((s) => ({ toasts: [...s.toasts.slice(-3), { ...toast, id }] }));
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 4200);
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

/** Imperative helpers usable from anywhere (event handlers, mutations). */
export const toast = {
  success: (title: string, description?: string) => useToastStore.getState().push({ title, description, tone: "success" }),
  error: (title: string, description?: string) => useToastStore.getState().push({ title, description, tone: "error" }),
  info: (title: string, description?: string) => useToastStore.getState().push({ title, description, tone: "info" }),
  warning: (title: string, description?: string) => useToastStore.getState().push({ title, description, tone: "warning" }),
};

const toneStyles: Record<ToastTone, { icon: typeof Info; wrap: string; iconColor: string }> = {
  success: { icon: CheckCircle2, wrap: "bg-emerald-50 text-emerald-700", iconColor: "text-emerald-600" },
  error: { icon: XCircle, wrap: "bg-red-50 text-red-700", iconColor: "text-red-600" },
  info: { icon: Info, wrap: "bg-sky-50 text-sky-700", iconColor: "text-sky-600" },
  warning: { icon: AlertTriangle, wrap: "bg-yellow-50 text-yellow-700", iconColor: "text-yellow-600" },
};

export function Toaster() {
  const { toasts, dismiss } = useToastStore();
  return (
    <div className="pointer-events-none fixed right-4 top-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {toasts.map((t) => {
        const { icon: Icon, wrap, iconColor } = toneStyles[t.tone];
        return (
          <div
            key={t.id}
            role="status"
            className={`toast-enter pointer-events-auto flex items-start gap-3 rounded-xl border border-[var(--border)] bg-white p-3 shadow-lg shadow-black/5 ${wrap}`}
          >
            <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${iconColor}`} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">{t.title}</p>
              {t.description && <p className="mt-0.5 text-xs opacity-80">{t.description}</p>}
            </div>
            <button
              type="button"
              aria-label="Dismiss notification"
              onClick={() => dismiss(t.id)}
              className="grid h-6 w-6 shrink-0 place-items-center rounded-md transition-colors hover:bg-black/5"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
