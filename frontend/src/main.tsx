import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ErrorBoundary } from "@/core/components/ErrorBoundary";
import { Layout } from "@/core/components/Layout";
import { ProtectedRoute } from "@/core/components/ProtectedRoute";
import { Toaster } from "@/core/components/ui/toast";
import { type ModuleRoute } from "@/core/lib/routes";
import { Landing } from "@/modules/common/Landing";
import { Login } from "@/modules/common/Login";
import { moduleRoutes as adminRoutes } from "@/modules/admin/routes";
import { moduleRoutes as commonRoutes } from "@/modules/common/routes";
import { moduleRoutes as facultyRoutes } from "@/modules/faculty/routes";
import { moduleRoutes as placementRoutes } from "@/modules/placement/routes";
import { moduleRoutes as studentRoutes } from "@/modules/student/routes";

import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
});

function registerSW() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
}

function App() {
  useEffect(() => {
    registerSW();

    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      console.error("[UnhandledRejection]", event.reason);
      event.preventDefault();
    };
    const onError = (event: ErrorEvent) => {
      console.error("[GlobalError]", event.error);
    };
    window.addEventListener("unhandledrejection", onUnhandledRejection);
    window.addEventListener("error", onError);
    return () => {
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
      window.removeEventListener("error", onError);
    };
  }, []);

  const appRoutes: ModuleRoute[] = [
    ...commonRoutes,
    ...studentRoutes,
    ...facultyRoutes,
    ...placementRoutes,
    ...adminRoutes,
  ];

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Landing />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            {appRoutes.map((route) => (
              <Route
                key={route.path}
                path={route.path}
                element={
                  route.roles ? <ProtectedRoute roles={route.roles}>{route.element}</ProtectedRoute> : route.element
                }
              />
            ))}
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
