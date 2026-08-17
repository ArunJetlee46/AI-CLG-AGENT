import {
  BarChart3,
  BookOpen,
  Bot,
  Brain,
  ChevronLeft,
  ClipboardCheck,
  ClipboardList,
  Code2,
  CopyX,
  FileBarChart,
  FileText,
  FlaskConical,
  GraduationCap,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  Menu,
  Presentation,
  Rocket,
  ScrollText,
  Search,
  ShieldCheck,
  Target,
  Megaphone,
  Building2,
  FileSearch,
  ListChecks,
  Home,
  Sparkles,
  TestTube2,
  TrendingUp,
  Trophy,
  UserCog,
  UserX,
  Users,
  Wrench,
  Award,
  Boxes,
  CalendarClock,
  DatabaseBackup,
  Handshake,
  HeartPulse,
  Landmark,
  Waves,
  X,
  MessagesSquare,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { scheduleProactiveRefresh } from "@/core/lib/auth-session";
import { authApi } from "@/core/lib/api";
import { cn } from "@/core/lib/utils";
import { useAuthStore } from "@/core/stores/auth";
import { NotificationBell } from "@/core/components/NotificationBell";

const NAV_SECTIONS: { title: string; items: { to: string; label: string; icon: typeof Bot; roles?: string[] }[] }[] = [
  {
    title: "Placement",
    items: [
      { to: "/placement", label: "Placement Welcome", icon: Home, roles: ["placement"] },
      { to: "/placement/dashboard", label: "Placement Dashboard", icon: LayoutDashboard, roles: ["placement"] },
      { to: "/placement/jd", label: "JD Analyzer", icon: FileSearch, roles: ["placement"] },
      { to: "/placement/matching", label: "Job–Student Matching", icon: Users, roles: ["placement"] },
      { to: "/placement/drives", label: "Drives & Rounds", icon: ListChecks, roles: ["placement"] },
      { to: "/placement/analytics", label: "Placement Analytics", icon: BarChart3, roles: ["placement"] },
      { to: "/placement/gaps", label: "Gaps & Training", icon: Target, roles: ["placement"] },
      { to: "/placement/companies", label: "Company CRM", icon: Building2, roles: ["placement"] },
      { to: "/placement/notifications", label: "Notifications", icon: Megaphone, roles: ["placement"] },
      { to: "/placement/announcements", label: "Announcements", icon: Megaphone, roles: ["placement"] },
      { to: "/placement/reports", label: "Placement Reports", icon: FileText, roles: ["placement"] },
    ],
  },
  {
    title: "Assistants",
    items: [
      { to: "/chat", label: "AI Assistant", icon: Bot, roles: ["student", "lecturer", "placement"] },
      { to: "/student", label: "Student Home", icon: GraduationCap, roles: ["student"] },
      { to: "/student/dashboard", label: "My Dashboard", icon: LayoutDashboard, roles: ["student"] },
      { to: "/student/insights", label: "My Insights", icon: TrendingUp, roles: ["student"] },
      { to: "/student/community", label: "Community", icon: Trophy, roles: ["student"] },
      { to: "/student/schedule", label: "My Schedule", icon: CalendarClock, roles: ["student"] },
      { to: "/student/placements", label: "My Placements", icon: Handshake, roles: ["student"] },
      { to: "/student/study-assist", label: "Study Assistant", icon: MessagesSquare, roles: ["student"] },
      { to: "/student/exam-prep", label: "Exam Prep", icon: BookOpen, roles: ["student"] },
      { to: "/student/assignment-assistant", label: "Assignments", icon: ClipboardList, roles: ["student"] },
      { to: "/student/mock-interview", label: "Mock Interview", icon: Users, roles: ["student"] },
      { to: "/student/resume-ats", label: "Resume ATS", icon: FileText, roles: ["student"] },
      { to: "/student/project-mentor", label: "Project Mentor", icon: Rocket, roles: ["student"] },
      { to: "/faculty", label: "Faculty", icon: Users, roles: ["lecturer"] },
      { to: "/faculty/copilot", label: "Faculty Copilot", icon: Bot, roles: ["lecturer"] },
      { to: "/faculty/announcements", label: "Announcements", icon: Megaphone, roles: ["lecturer"] },
      { to: "/faculty/dashboard", label: "My Dashboard", icon: LayoutDashboard, roles: ["lecturer"] },
      { to: "/faculty/audit", label: "Audit Log", icon: ScrollText, roles: ["lecturer"] },
      { to: "/faculty/intelligence", label: "Faculty Intelligence", icon: Brain, roles: ["lecturer"] },
      { to: "/faculty/course-reports", label: "Course Reports", icon: FileBarChart, roles: ["lecturer"] },
      { to: "/faculty/remedial", label: "Remedial Plans", icon: LifeBuoy, roles: ["lecturer"] },
      { to: "/faculty/schedule", label: "My Schedule", icon: CalendarClock, roles: ["lecturer"] },
      { to: "/faculty/placements", label: "Placement Overview", icon: Handshake, roles: ["lecturer"] },
      { to: "/faculty/similarity", label: "Similarity Check", icon: CopyX, roles: ["lecturer"] },
      { to: "/admin", label: "Command Center", icon: ShieldCheck, roles: ["admin"] },
    ],
  },
  {
    title: "Faculty Tools",
    items: [
      { to: "/faculty/tools", label: "All Tools", icon: Wrench, roles: ["lecturer"] },
      { to: "/faculty/tools/question-paper", label: "Question Paper", icon: FileText, roles: ["lecturer"] },
      { to: "/faculty/tools/lesson-plan", label: "Lesson Plan", icon: Presentation, roles: ["lecturer"] },
      { to: "/faculty/tools/teaching-material", label: "Teaching Material", icon: BookOpen, roles: ["lecturer"] },
      { to: "/faculty/tools/assignment-eval", label: "Assignment Evaluation", icon: ClipboardCheck, roles: ["lecturer"] },
      { to: "/faculty/tools/code-review", label: "Code Review", icon: Code2, roles: ["lecturer"] },
      { to: "/faculty/tools/lab-assistant", label: "Lab Assistant", icon: FlaskConical, roles: ["lecturer"] },
      { to: "/faculty/tools/viva-questions", label: "Viva Questions", icon: TestTube2, roles: ["lecturer"] },
    ],
  },
  {
    title: "Insights",
    items: [{ to: "/analytics", label: "Analytics", icon: BarChart3, roles: ["lecturer"] }],
  },
  {
    title: "Admin Center",
    items: [
      { to: "/admin/users", label: "User Management", icon: UserCog, roles: ["admin"] },
      { to: "/admin/departments", label: "Departments", icon: Building2, roles: ["admin"] },
      { to: "/admin/announcements", label: "Announcements", icon: Megaphone, roles: ["admin"] },
      { to: "/admin/resources", label: "Resources", icon: Boxes, roles: ["admin"] },
      { to: "/admin/backups", label: "Backups", icon: DatabaseBackup, roles: ["admin"] },
      { to: "/admin/models", label: "Model Registry", icon: Brain, roles: ["admin"] },
      { to: "/admin/analytics/students", label: "Student Analytics", icon: GraduationCap, roles: ["admin"] },
      { to: "/admin/analytics/faculty", label: "Faculty Analytics", icon: Users, roles: ["admin"] },
      { to: "/admin/analytics/placement", label: "Placement Analytics", icon: BarChart3, roles: ["admin"] },
      { to: "/admin/analytics/dropout", label: "Dropout Risk", icon: UserX, roles: ["admin"] },
      { to: "/admin/analytics/curriculum", label: "Curriculum Intelligence", icon: BookOpen, roles: ["admin"] },
      { to: "/admin/analytics/enrollment-forecast", label: "Enrollment Forecast", icon: TrendingUp, roles: ["admin"] },
      { to: "/admin/analytics/accreditation", label: "Accreditation", icon: Award, roles: ["admin"] },
      { to: "/admin/research", label: "Research", icon: FlaskConical, roles: ["admin"] },
      { to: "/admin/industry", label: "Industry", icon: Handshake, roles: ["admin"] },
      { to: "/admin/approvals", label: "Approvals", icon: ClipboardCheck, roles: ["admin"] },
      { to: "/admin/audit", label: "Audit Center", icon: ScrollText, roles: ["admin"] },
      { to: "/admin/governance", label: "Governance", icon: Landmark, roles: ["admin"] },
      { to: "/admin/system-health", label: "System Health", icon: HeartPulse, roles: ["admin"] },
      { to: "/admin/copilot", label: "AI Admin Copilot", icon: Sparkles, roles: ["admin"] },
      { to: "/admin/digital-twin", label: "Digital Twin", icon: Waves, roles: ["admin"] },
      { to: "/admin/timetable", label: "Timetable Optimizer", icon: CalendarClock, roles: ["admin"] },
      { to: "/admin/evaluation", label: "Evaluation Center", icon: ClipboardCheck, roles: ["admin"] },
    ],
  },
];

const OVERVIEW_HOME: Record<string, { to: string; label: string; icon: typeof Bot }> = {
  student: { to: "/student", label: "Welcome", icon: GraduationCap },
  lecturer: { to: "/faculty", label: "Faculty", icon: Users },
  placement: { to: "/placement", label: "Placement Welcome", icon: Home },
  admin: { to: "/admin", label: "Command Center", icon: ShieldCheck },
};

const roleLabel: Record<string, string> = {
  student: "Student",
  lecturer: "Faculty",
  placement: "Placement Officer",
  admin: "Administrator",
};

const roleTheme: Record<string, { solid: string; soft: string; bar: string; card: string; text: string }> = {
  student: {
    solid: "from-sky-500 to-cyan-500",
    soft: "bg-sky-500/10 text-sky-600",
    bar: "bg-sky-600",
    card: "border-sky-500/25 bg-sky-500/[0.04]",
    text: "text-sky-600",
  },
  lecturer: {
    solid: "from-violet-500 to-purple-500",
    soft: "bg-violet-500/10 text-violet-600",
    bar: "bg-violet-600",
    card: "border-violet-500/25 bg-violet-500/[0.04]",
    text: "text-violet-600",
  },
  placement: {
    solid: "from-emerald-500 to-teal-500",
    soft: "bg-emerald-500/10 text-emerald-600",
    bar: "bg-emerald-600",
    card: "border-emerald-500/25 bg-emerald-500/[0.04]",
    text: "text-emerald-600",
  },
  admin: {
    solid: "from-[var(--primary)] to-violet-500",
    soft: "bg-[var(--primary)]/10 text-[var(--primary)]",
    bar: "bg-[var(--primary)]",
    card: "border-[var(--primary)]/30 bg-[var(--primary)]/[0.04]",
    text: "text-[var(--primary)]",
  },
};

function buildSections(role: string | null) {
  const home = OVERVIEW_HOME[role ?? ""] ?? { to: "/student", label: "My Space", icon: GraduationCap };
  const sections = [
    { title: "Overview", items: [{ ...home, roles: undefined }] },
    ...NAV_SECTIONS,
  ]
    .map((section) => ({
      ...section,
      items: section.items.filter(
        (item) =>
          (!item.roles || (role && item.roles.includes(role))) &&
          (section.title === "Overview" || item.to !== home.to)
      ),
    }))
    .filter((section) => section.items.length > 0);
  return sections;
}

function useSidebarState() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem("beru:sidebar-collapsed") === "1";
    } catch {
      return false;
    }
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      try {
        localStorage.setItem("beru:sidebar-collapsed", prev ? "0" : "1");
      } catch {
        /* ignore */
      }
      return !prev;
    });
  }, []);

  return { collapsed, toggleCollapsed, mobileOpen, setMobileOpen };
}

export function Layout() {
  const { username, role, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const { collapsed, toggleCollapsed, mobileOpen, setMobileOpen } = useSidebarState();
  const [query, setQuery] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  const theme = roleTheme[role ?? ""] ?? roleTheme.admin;
  const sections = useMemo(() => buildSections(role ?? null), [role]);

  const filteredSections = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sections;
    return sections
      .map((s) => ({ ...s, items: s.items.filter((i) => i.label.toLowerCase().includes(q)) }))
      .filter((s) => s.items.length > 0);
  }, [sections, query]);

  // Breadcrumb trail from the current path.
  const crumbs = useMemo(() => {
    const all = sections.flatMap((s) => s.items);
    const exact = all.find((i) => i.to === location.pathname);
    if (exact) return [{ to: exact.to, label: exact.label }];
    const parent = all
      .filter((i) => i.to !== "/" && location.pathname.startsWith(i.to))
      .sort((a, b) => b.to.length - a.to.length)[0];
    if (!parent) return [];
    const childLabel = location.pathname.split("/").filter(Boolean).pop()?.replace(/-/g, " ");
    return [
      { to: parent.to, label: parent.label },
      childLabel ? { to: location.pathname, label: childLabel } : null,
    ].filter(Boolean) as { to: string; label: string }[];
  }, [sections, location.pathname]);

  // Close the mobile drawer on navigation.
  useEffect(() => {
    setMobileOpen(false);
    setQuery("");
  }, [location.pathname, setMobileOpen]);

  // Cmd/Ctrl+K focuses the page search.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setMobileOpen(false);
        searchRef.current?.focus();
        searchRef.current?.select();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [setMobileOpen]);

  // Validate the stored session on load and arm the proactive refresh timer.
  useEffect(() => {
    const { token } = useAuthStore.getState();
    scheduleProactiveRefresh();
    if (!token) return;
    void authApi.me(token).catch(() => {});
  }, []);

  const closeDrawer = () => setMobileOpen(false);

  return (
    <div className="app-bg flex min-h-screen" data-role={role ?? "admin"}>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm lg:hidden" onClick={closeDrawer} aria-hidden />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r border-[var(--border)] bg-white/90 backdrop-blur transition-[width,transform] duration-300",
          "lg:sticky lg:top-0 lg:h-screen",
          collapsed ? "lg:w-[76px]" : "lg:w-64",
          mobileOpen ? "w-64 translate-x-0" : "w-64 -translate-x-full lg:translate-x-0"
        )}
      >
        <div className={cn("flex items-center gap-2.5 px-3 pb-5 pt-4", collapsed && "lg:justify-center lg:px-0")}>
          <span className={cn("grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br text-white shadow-md", theme.solid)}>
            <Sparkles className="h-5 w-5" />
          </span>
          {!collapsed && (
            <div className="min-w-0 leading-tight">
              <p className="truncate text-sm font-bold tracking-tight">Beru Campus AI</p>
              <p className="truncate text-[11px] text-[var(--muted-foreground)]">Autonomous campus</p>
            </div>
          )}
        </div>

        {!collapsed && (
          <div className="relative mb-2 px-3">
            <Search className="pointer-events-none absolute left-5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search pages…  (Ctrl K)"
              className="h-9 w-full rounded-lg border border-[var(--border)] bg-[var(--muted)]/50 pl-9 pr-3 text-sm placeholder:text-[var(--muted-foreground)] focus:border-[var(--primary)]/40 focus:bg-white focus:outline-none"
            />
          </div>
        )}

        <nav className="flex flex-1 flex-col gap-4 overflow-y-auto px-3 pb-3">
          {filteredSections.map((section) => (
            <div key={section.title} className="flex flex-col gap-1">
              {!collapsed && (
                <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  {section.title}
                </p>
              )}
              {section.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  title={collapsed ? label : undefined}
                  className={({ isActive }) =>
                    cn(
                      "group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors",
                      collapsed && "lg:justify-center lg:px-0",
                      isActive
                        ? theme.soft
                        : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <span
                        className={cn(
                          "absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full transition-opacity",
                          isActive ? "opacity-100" : "opacity-0",
                          theme.bar
                        )}
                      />
                      <Icon
                        className={cn(
                          "h-4 w-4 shrink-0 transition-colors",
                          isActive ? theme.text : "text-[var(--muted-foreground)] group-hover:text-[var(--foreground)]"
                        )}
                      />
                      {!collapsed && <span className="truncate">{label}</span>}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="mt-auto border-t border-[var(--border)] px-3 py-3">
          <div className={cn("flex items-center gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2.5 transition-colors", collapsed && "lg:justify-center lg:px-0")}>
            <span
              className={cn(
                "grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br text-sm font-bold text-white",
                theme.solid
              )}
            >
              {(username ?? "?").charAt(0).toUpperCase()}
            </span>
            {!collapsed && (
              <div className="min-w-0 flex-1 leading-tight">
                <p className="truncate text-sm font-semibold">{username}</p>
                <p className="truncate text-[11px] text-[var(--muted-foreground)]">{roleLabel[role ?? ""] ?? role}</p>
              </div>
            )}
            {!collapsed && (
              <button
                type="button"
                aria-label="Sign out"
                onClick={() => {
                  logout();
                  navigate("/login");
                }}
                className="grid h-7 w-7 shrink-0 place-items-center rounded-md text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--destructive)]"
              >
                <LogOut className="h-4 w-4" />
              </button>
            )}
          </div>
          <button
            type="button"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={toggleCollapsed}
            className="mt-2 hidden w-full items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--foreground)] lg:flex"
          >
            <ChevronLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
            {!collapsed && "Collapse"}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-[var(--border)] bg-white/80 px-4 py-3 backdrop-blur lg:hidden">
          <button
            type="button"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
            className="grid h-9 w-9 place-items-center rounded-lg border border-[var(--border)] text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)]"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <span className={cn("grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br text-white", theme.solid)}>
            <Sparkles className="h-4 w-4" />
          </span>
          <p className="truncate text-sm font-bold">Beru Campus AI</p>
          <span className="ml-auto inline-flex lg:hidden">
            <NotificationBell />
          </span>
          <button
            type="button"
            aria-label="Sign out"
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="grid h-9 w-9 place-items-center rounded-lg border border-[var(--border)] text-[var(--muted-foreground)] transition-colors hover:text-[var(--destructive)]"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-8 lg:px-10 lg:py-8">
          {/* Breadcrumbs */}
          {crumbs.length > 0 && (
            <div className="mb-4 flex items-center justify-between gap-3">
              <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                <span className="font-medium text-[var(--foreground)]">Beru Campus AI</span>
                {crumbs.map((c, i) => (
                  <span key={c.to} className="flex items-center gap-1.5">
                    <span className="opacity-40">/</span>
                    {i === crumbs.length - 1 ? (
                      <span className="font-medium capitalize text-[var(--muted-foreground)]">{c.label}</span>
                    ) : (
                      <NavLink to={c.to} className="capitalize transition-colors hover:text-[var(--primary)]">
                        {c.label}
                      </NavLink>
                    )}
                  </span>
                ))}
              </nav>
              <span className="hidden shrink-0 lg:inline-flex">
                <NotificationBell />
              </span>
            </div>
          )}

          {/* Keyed wrapper re-triggers the fade-up transition on navigation. */}
          <div key={location.pathname} className="fade-up">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
