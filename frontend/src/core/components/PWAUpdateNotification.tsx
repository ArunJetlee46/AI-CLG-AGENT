import { useEffect, useState } from "react";
import { Download, X, RefreshCw } from "lucide-react";
import { Button } from "@/core/components/ui/button";
import { cn } from "@/core/lib/utils";

export function PWAUpdateNotification() {
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    const checkForUpdate = async () => {
      const registration = await navigator.serviceWorker.ready;
      registration.update().catch(() => {});
    };

    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (navigator.serviceWorker.controller) {
        setUpdateAvailable(true);
      }
    });

    navigator.serviceWorker.addEventListener("message", (event) => {
      if (event.data && event.data.type === "SW_UPDATED") {
        setUpdateAvailable(true);
      }
    });

    checkForUpdate();
    const interval = setInterval(checkForUpdate, 60000);

    return () => clearInterval(interval);
  }, []);

  const applyUpdate = async () => {
    if (!("serviceWorker" in navigator)) return;
    const registration = await navigator.serviceWorker.ready;
    if (registration.waiting) {
      registration.waiting.postMessage({ type: "SKIP_WAITING" });
    }
    window.location.reload();
  };

  if (!updateAvailable || dismissed) return null;

  return (
    <div
      className={cn(
        "fixed bottom-4 right-4 z-50 animate-slide-up",
        "rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-xl p-4 max-w-sm"
      )}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <RefreshCw className="h-5 w-5 text-sky-600 animate-spin" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--foreground)]">
            New version available
          </p>
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">
            Refresh to get the latest features and fixes.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="default" onClick={applyUpdate}>
            <Download className="mr-1.5 h-3.5 w-3.5" /> Update
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setDismissed(true)}>
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}