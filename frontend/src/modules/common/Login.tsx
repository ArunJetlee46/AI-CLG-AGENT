import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowRight,
  Bot,
  Briefcase,
  Clock3,
  Eye,
  EyeOff,
  GraduationCap,
  KeyRound,
  LineChart,
  Lock,
  ShieldCheck,
  Sparkles,
  User,
  Users,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { scheduleProactiveRefresh } from "@/core/lib/auth-session";
import { Button } from "@/core/components/ui/button";
import { Input } from "@/core/components/ui/input";
import { toast } from "@/core/components/ui/toast";
import { authApi } from "@/core/lib/api";
import { cn } from "@/core/lib/utils";
import { useAuthStore } from "@/core/stores/auth";

const ROLES: {
  key: "student" | "lecturer" | "placement" | "admin";
  label: string;
  icon: LucideIcon;
  title: string;
  subtitle: string;
  accent: string;
  active: string;
  panel: string;
}[] = [
  {
    key: "student",
    label: "Student",
    icon: GraduationCap,
    title: "Student Portal",
    subtitle: "Your courses, attendance and personal risk outlook",
    accent: "text-sky-600",
    active: "bg-sky-600 text-white shadow-lg shadow-sky-600/40",
    panel: "from-sky-600 via-sky-500 to-cyan-600",
  },
  {
    key: "lecturer",
    label: "Faculty",
    icon: Users,
    title: "Faculty Portal",
    subtitle: "Class performance and at-risk students",
    accent: "text-violet-600",
    active: "bg-violet-600 text-white shadow-lg shadow-violet-600/40",
    panel: "from-violet-600 via-purple-600 to-fuchsia-600",
  },
  {
    key: "placement",
    label: "Placement",
    icon: Briefcase,
    title: "Placement Officer",
    subtitle: "Readiness scoring, shortlisting and placement intelligence",
    accent: "text-emerald-600",
    active: "bg-emerald-600 text-white shadow-lg shadow-emerald-600/40",
    panel: "from-emerald-600 via-teal-500 to-teal-600",
  },
  {
    key: "admin",
    label: "Admin",
    icon: ShieldCheck,
    title: "Admin Console",
    subtitle: "Command center, governance and system control",
    accent: "text-[var(--primary)]",
    active: "bg-[var(--primary)] text-white shadow-lg shadow-[var(--primary)]/40",
    panel: "from-[var(--primary)] via-indigo-600 to-indigo-700",
  },
];

type RoleKey = (typeof ROLES)[number]["key"];

const DEMO_CREDENTIALS: Record<RoleKey, [string, string]> = {
  student: ["student", "student123"],
  lecturer: ["lecturer", "lecturer123"],
  placement: ["placement", "placement123"],
  admin: ["admin", "admin123"],
};

const roleHome: Record<string, string> = {
  student: "/student",
  lecturer: "/faculty",
  placement: "/placement",
  admin: "/admin",
};

const HIGHLIGHTS: { icon: LucideIcon; title: string; text: string }[] = [
  {
    icon: Bot,
    title: "Role-aware copilots",
    text: "Student, faculty, placement and admin assistants tuned to each job.",
  },
  {
    icon: LineChart,
    title: "Predictive analytics",
    text: "Pass probabilities, readiness scores and risk signals from real data.",
  },
  {
    icon: ShieldCheck,
    title: "Governance built in",
    text: "Approval gates and a tamper-evident audit trail on every action.",
  },
];

export function Login() {
  const [searchParams] = useSearchParams();
  const requestedRole = searchParams.get("role");
  const expired = searchParams.get("expired") === "1";
  const initialRole: RoleKey = ROLES.some((r) => r.key === requestedRole)
    ? (requestedRole as RoleKey)
    : "admin";
  const [selectedRole, setSelectedRole] = useState<RoleKey>(initialRole);
  const [draft, setDraft] = useState<[string, string]>(DEMO_CREDENTIALS[initialRole]);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { token, refreshToken, role, setAuth } = useAuthStore();
  const navigate = useNavigate();
  const usernameRef = useRef<HTMLInputElement>(null);

  const current = ROLES.find((r) => r.key === selectedRole)!;

  useEffect(() => {
    if (token && refreshToken) {
      navigate(roleHome[role ?? ""] ?? "/student", { replace: true });
    }
  }, [token, refreshToken, navigate]);

  function selectRole(role: RoleKey) {
    if (role === selectedRole) return;
    setSelectedRole(role);
    setDraft(DEMO_CREDENTIALS[role]);
    setError(null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!draft[0].trim() || !draft[1]) {
      setError("Enter your username and password.");
      usernameRef.current?.focus();
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const tokens = await authApi.login(draft[0].trim(), draft[1].trim());
      const me = await authApi.me(tokens.access_token);
      setAuth(tokens.access_token, me.role, me.username, tokens.refresh_token);
      scheduleProactiveRefresh();
      toast.success(`Welcome, ${me.username}`, current.title);
      navigate(roleHome[me.role] ?? "/student");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      toast.error("Sign in failed", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-bg flex min-h-screen">
      {/* ---------- Brand panel (desktop) ---------- */}
      <aside className={`relative hidden w-[44%] max-w-xl flex-col justify-between overflow-hidden border-r border-[var(--border)] bg-gradient-to-br p-10 text-white transition-colors duration-500 lg:flex ${current.panel}`}>
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-20 h-96 w-96 rounded-full bg-emerald-400/20 blur-3xl" />
        <div className="pointer-events-none absolute right-8 top-1/3 h-40 w-40 rounded-full bg-white/5 blur-2xl" />

        <div className="relative flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-white/15 text-white backdrop-blur">
            <Sparkles className="h-5 w-5" />
          </span>
          <div className="leading-tight">
            <p className="text-base font-bold tracking-tight">Beru Campus AI</p>
            <p className="text-xs text-white/70">Autonomous campus workforce</p>
          </div>
        </div>

        <div className="relative">
          <span className="mb-5 inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-medium backdrop-blur">
            <Zap className="h-3.5 w-3.5" /> Role-aware AI for every campus stakeholder
          </span>
          <h1 className="max-w-md text-3xl font-extrabold leading-tight tracking-tight xl:text-4xl">
            An AI workforce that runs the campus.
          </h1>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-white/75">
            Predict, explain and act — backed by a grounded knowledge base, approval gates and a
            tamper-evident audit trail. You stay in control.
          </p>

          <div className="mt-8 flex flex-col gap-4">
            {HIGHLIGHTS.map(({ icon: Icon, title, text }) => (
              <div key={title} className="flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white/15 backdrop-blur">
                  <Icon className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-sm font-semibold">{title}</p>
                  <p className="text-xs text-white/70">{text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-white/60">
          Student · Faculty · Placement · Admin copilots with governance baked in.
        </p>
      </aside>

      {/* ---------- Form panel ---------- */}
      <main className="flex flex-1 items-center justify-center px-4 py-10 sm:px-6">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="mb-8 flex flex-col items-center gap-2 text-center lg:hidden">
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-[var(--primary)] to-violet-500 text-white shadow-xl shadow-[var(--primary)]/30">
              <Sparkles className="h-7 w-7" />
            </span>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">Beru Campus AI</h1>
              <p className="text-sm text-[var(--muted-foreground)]">
                An AI workforce that runs the campus
              </p>
            </div>
          </div>

          {/* Role switcher */}
          <div className="fade-up grid grid-cols-4 gap-1 rounded-xl border border-[var(--border)] bg-white/70 p-1 shadow-sm backdrop-blur">
            {ROLES.map((role) => {
              const Icon = role.icon;
              const isActive = role.key === selectedRole;
              return (
                <button
                  key={role.key}
                  type="button"
                  onClick={() => selectRole(role.key)}
                  aria-pressed={isActive}
                  title={`${role.title} — ${role.subtitle}`}
                  className={cn(
                    "flex flex-col items-center gap-1 rounded-lg px-1 py-2 text-[11px] font-medium transition-all duration-200",
                    isActive ? role.active : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {role.label}
                </button>
              );
            })}
          </div>

          {/* Expired-session notice */}
          {expired && (
            <div
              role="alert"
              className="fade-up mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
            >
              <Clock3 className="mt-0.5 h-4 w-4 shrink-0" />
              <span>Your session expired. Please sign in again to continue.</span>
            </div>
          )}

          {/* Sign-in card — keyed by role so it re-animates on switch */}
          <form
            key={selectedRole}
            onSubmit={handleSubmit}
            className="fade-up mt-4 flex flex-col gap-5 rounded-2xl border border-[var(--border)] bg-white/90 p-6 shadow-xl shadow-black/5 backdrop-blur sm:p-7"
          >
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "grid h-11 w-11 place-items-center rounded-xl shadow-md",
                  current.active
                )}
              >
                <current.icon className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <h2 className="text-lg font-bold leading-tight">{current.title}</h2>
                <p className="truncate text-xs text-[var(--muted-foreground)]">{current.subtitle}</p>
              </div>
            </div>

            <div className="flex flex-col gap-4">
              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold text-[var(--muted-foreground)]">Username</span>
                <div className="relative">
                  <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
                  <Input
                    ref={usernameRef}
                    value={draft[0]}
                    onChange={(e) => setDraft(([_, p]) => [e.target.value, p])}
                    placeholder="e.g. admin"
                    autoComplete="username"
                    spellCheck={false}
                    className="pl-9"
                  />
                </div>
              </label>

              <label className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold text-[var(--muted-foreground)]">Password</span>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
                  <Input
                    type={showPassword ? "text" : "password"}
                    value={draft[1]}
                    onChange={(e) => setDraft(([u]) => [u, e.target.value])}
                    placeholder="••••••••"
                    autoComplete="current-password"
                    className="pl-9 pr-10"
                  />
                  <button
                    type="button"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-md text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                  >
                    {showPassword ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                  </button>
                </div>
              </label>
            </div>

            {error && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
                {error}
              </p>
            )}

            <Button type="submit" loading={loading} size="lg" className={cn("w-full", current.active)}>
              {loading ? "Signing in…" : `Continue as ${current.label}`}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </Button>

            <p className="flex items-center justify-center gap-1.5 text-center text-xs text-[var(--muted-foreground)]">
              <KeyRound className="h-3.5 w-3.5" /> Demo credentials are pre-filled for each role
            </p>
          </form>
        </div>
      </main>
    </div>
  );
}
