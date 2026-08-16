import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { HelpAssistant } from "@/core/components/HelpAssistant";
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

function registerSW() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
}

function App() {
  useEffect(() => {
    registerSW();
  }, []);

  const appRoutes: ModuleRoute[] = [
    ...commonRoutes,
    ...studentRoutes,
    ...facultyRoutes,
    ...placementRoutes,
    ...adminRoutes,
  ];

  const queryClient = new QueryClient();

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
        <HelpAssistant />
        <Toaster />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

const appRoutes: ModuleRoute[] = [
  ...commonRoutes,
  ...studentRoutes,
  ...facultyRoutes,
  ...placementRoutes,
  ...adminRoutes,
];

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
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
        <HelpAssistant />
        <Toaster />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
