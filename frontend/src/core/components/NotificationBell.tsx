import { useEffect, useRef, useState, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Award,
  Bell,
  Briefcase,
  Building2,
  CheckCheck,
  Megaphone,
  type LucideIcon,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { notificationsApi, type NotificationItem } from "@/core/lib/api";
import { useAuthStore } from "@/core/stores/auth";
import { cn } from "@/core/lib/utils";
import { useWebSocket } from "@/core/hooks/useWebSocket";

const TYPE_STYLES: Record<string, { icon: LucideIcon; cls: string }> = {
  risk: { icon: AlertTriangle, cls: "bg-red-100 text-red-600" },
  shortlist: { icon: Briefcase, cls: "bg-emerald-100 text-emerald-600" },
  milestone: { icon: Award, cls: "bg-amber-100 text-amber-600" },
  announcement: { icon: Megaphone, cls: "bg-indigo-100 text-indigo-600" },
  drive: { icon: Building2, cls: "bg-sky-100 text-sky-600" },
};

function timeAgo(iso: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

function createNotificationItem(data: unknown): NotificationItem {
  const d = data as Record<string, unknown>;
  return {
    id: `ws-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    type: (d.type as string) ?? "announcement",
    severity: (d.severity as string) ?? "info",
    title: (d.title as string) ?? "New notification",
    body: (d.body as string) ?? "",
    read: false,
    created_at: new Date().toISOString(),
    link: (d.link as string) ?? undefined,
  };
}

export function NotificationBell() {
  const token = useAuthStore((s) => s.token);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const [entries, setEntries] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const { data } = useQuery({
    queryKey: ["notifs"],
    queryFn: () => notificationsApi.list(token!),
    enabled: !!token,
    refetchInterval: 60_000,
  });

  useEffect(() => {
    if (data?.entries) {
      setEntries(data.entries);
      setUnreadCount(data.unread_count ?? 0);
    }
  }, [data]);

  const markRead = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id, token!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifs"] }),
  });

  const markAll = useMutation({
    mutationFn: () => notificationsApi.markAllRead(token!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifs"] }),
  });

  const handleWsNotification = useCallback((_event: string, data: unknown) => {
    const newItem = createNotificationItem(data);
    setEntries((prev) => [newItem, ...prev]);
    setUnreadCount((prev) => prev + 1);
    qc.invalidateQueries({ queryKey: ["notifs"] });
  }, [qc]);

  useWebSocket({
    onNotification: handleWsNotification,
    onConnect: () => qc.invalidateQueries({ queryKey: ["notifs"] }),
  });

  useEffect(() => {
    if (!open) return;
    function onDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function openItem(item: NotificationItem) {
    if (!item.read) markRead.mutate(item.id);
    setOpen(false);
    if (item.link) navigate(item.link);
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ""}`}
        onClick={() => setOpen((v) => !v)}
        className="relative grid h-9 w-9 place-items-center rounded-lg border border-[var(--border)] text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -right-1.5 -top-1.5 grid h-4 min-w-4 place-items-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-[min(92vw,26rem)] overflow-hidden rounded-xl border border-[var(--border)] bg-white shadow-2xl shadow-black/10">
          <div className="flex items-center justify-between gap-2 border-b border-[var(--border)] px-3 py-2">
            <p className="text-sm font-bold">Notifications</p>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={() => markAll.mutate()}
                disabled={markAll.isPending}
                className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] transition-colors hover:underline disabled:opacity-50"
              >
                <CheckCheck className="h-3.5 w-3.5" /> Mark all read
              </button>
            )}
          </div>

          <div className="max-h-[22rem] overflow-y-auto p-1.5">
            {entries.length === 0 && (
              <p className="px-3 py-8 text-center text-sm text-[var(--muted-foreground)]">
                No notifications yet.
              </p>
            )}
            {entries.map((item) => {
              const meta =
                TYPE_STYLES[item.type] ?? { icon: Bell, cls: "bg-[var(--muted)] text-[var(--muted-foreground)]" };
              const Icon = meta.icon;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => openItem(item)}
                  className={cn(
                    "flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-[var(--muted)]",
                    !item.read && "bg-[var(--muted)]/60"
                  )}
                >
                  <span className={cn("mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg", meta.cls)}>
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-1.5">
                      <span className="min-w-0 flex-1 truncate text-sm font-semibold">{item.title}</span>
                      {!item.read && <span className="h-2 w-2 shrink-0 rounded-full bg-[var(--primary)]" />}
                    </span>
                    <span className="mt-0.5 block text-xs leading-snug text-[var(--muted-foreground)]">{item.body}</span>
                    <span className="mt-1 block text-[10px] text-[var(--muted-foreground)]">{timeAgo(item.created_at)}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
