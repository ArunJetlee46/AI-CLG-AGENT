import {
  ArrowRight,
  Bot,
  Briefcase,
  FileSearch,
  GraduationCap,
  LineChart,
  ShieldCheck,
  ShieldCheck as ShieldCheckIcon,
  Sparkles,
  Trophy,
  Users,
  Zap,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/core/components/ui/button";
import { useAuthStore } from "@/core/stores/auth";
import { RoleHome } from "@/modules/common/Home";

const PORTALS = [
  {
    key: "student",
    label: "Student",
    icon: GraduationCap,
    title: "Student Copilot",
    blurb: "Personal success score, digital twin, exam prep, mock interviews, study partners and badges.",
    accent: "text-sky-600 bg-sky-100",
    features: ["Risk alerts & today plan", "Exam Prep & assignments", "Mock interview + resume ATS"],
  },
  {
    key: "lecturer",
    label: "Faculty",
    icon: Users,
    title: "Faculty Copilot",
    blurb: "Class performance analytics, at-risk student detection, predictions and intervention plans.",
    accent: "text-violet-600 bg-violet-100",
    features: ["At-risk detection", "Pass-probability predictions", "Intervention workflow"],
  },
  {
    key: "placement",
    label: "Placement",
    icon: Briefcase,
    title: "Placement Copilot",
    blurb: "Career-readiness scoring, automated shortlisting, placement intelligence and drive reports.",
    accent: "text-emerald-600 bg-emerald-100",
    features: ["Readiness scoring", "Role-based shortlisting", "Placement analytics"],
  },
  {
    key: "admin",
    label: "Admin",
    icon: ShieldCheck,
    title: "Command Center",
    blurb: "Governance, approvals, audit trail, safety controls and full system oversight.",
    accent: "text-[var(--primary)] bg-[var(--primary)]/10",
    features: ["Approval pipeline", "Immutable audit log", "Safety & model registry"],
  },
] as const;

const HIGHLIGHTS = [
  {
    icon: Bot,
    title: "AI Curriculum Tutor",
    text: "A grounded RAG assistant that answers from the college knowledge base — never fabricates policy.",
  },
  {
    icon: LineChart,
    title: "Predictive Analytics",
    text: "Per-course pass probabilities and projected GPA from real attendance, grades and prerequisite graphs.",
  },
  {
    icon: FileSearch,
    title: "Explainable AI",
    text: "Every decision comes with drivers, reasons and evidence — no black boxes in campus governance.",
  },
  {
    icon: ShieldCheckIcon,
    title: "Human-in-the-Loop",
    text: "Sensitive actions require approvals and are recorded on a hash-chained audit log.",
  },
];

export function Landing() {
  const token = useAuthStore((s) => s.token);
  if (token) return <RoleHome />;

  return (
    <div className="app-bg min-h-screen overflow-hidden">
      <div className="pointer-events-none fixed -left-48 -top-48 h-[36rem] w-[36rem] rounded-full bg-[var(--primary)]/10 blur-3xl" />
      <div className="pointer-events-none fixed -bottom-48 -right-48 h-[36rem] w-[36rem] rounded-full bg-emerald-500/10 blur-3xl" />

      <div className="relative mx-auto max-w-6xl px-6">
        <header className="flex items-center justify-between py-5">
          <div className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-[var(--primary)] to-violet-500 text-white shadow-md shadow-[var(--primary)]/30">
              <Sparkles className="h-4 w-4" />
            </span>
            <div className="leading-tight">
              <p className="text-sm font-bold">Beru Campus AI</p>
              <p className="text-[11px] text-[var(--muted-foreground)]">Autonomous campus workforce</p>
            </div>
          </div>
          <Link to="/login">
            <Button variant="outline" size="sm">
              Sign in <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
            </Button>
          </Link>
        </header>

        <section className="grid grid-cols-1 items-center gap-10 py-16 lg:grid-cols-2 lg:py-24">
          <div className="fade-up">
            <div className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-white/70 px-3 py-1 text-xs text-[var(--muted-foreground)] backdrop-blur">
              <Zap className="h-3.5 w-3.5 text-[var(--primary)]" /> Role-aware AI for every campus stakeholder
            </div>
            <h1 className="text-4xl font-extrabold leading-tight tracking-tight lg:text-5xl">
              An AI workforce that runs the campus.
              <span className="bg-gradient-to-r from-[var(--primary)] to-violet-500 bg-clip-text text-transparent"> You stay in control.</span>
            </h1>
            <p className="mt-4 max-w-lg text-[var(--muted-foreground)]">
              Student, faculty, placement and admin copilots that predict, explain and act — backed by a
              grounded knowledge base, approval gates and a tamper-evident audit trail.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link to="/login">
                <Button size="lg">
                  Explore portals <ArrowRight className="ml-1.5 h-4 w-4" />
                </Button>
              </Link>
              <a href="#portals" className="rounded-full border border-[var(--border)] bg-white/70 px-4 py-2.5 text-sm font-medium backdrop-blur transition-colors hover:bg-[var(--muted)]">
                See what each role gets
              </a>
            </div>
          </div>

          <div className="fade-up grid grid-cols-2 gap-3">
            {[
              { icon: LineChart, value: "4", label: "Role-specific copilots" },
              { icon: Bot, value: "RAG", label: "Curriculum-grounded answers" },
              { icon: ShieldCheckIcon, value: "A*", label: "Hash-chained audit trail" },
              { icon: Trophy, value: "8+", label: "Student growth features" },
            ].map(({ icon: Icon, value, label }) => (
              <div key={label} className="card-shell rounded-2xl border border-[var(--border)] bg-white/80 p-5 backdrop-blur">
                <span className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--primary)]/10 text-[var(--primary)]">
                  <Icon className="h-4 w-4" />
                </span>
                <p className="mt-3 text-2xl font-extrabold">{value}</p>
                <p className="text-xs text-[var(--muted-foreground)]">{label}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="portals" className="py-10">
          <h2 className="text-center text-2xl font-bold tracking-tight">One platform, four portals</h2>
          <p className="mx-auto mt-2 max-w-xl text-center text-sm text-[var(--muted-foreground)]">
            Each role lands in its own command space with the tools that matter to it.
          </p>
          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {PORTALS.map((portal) => {
              const Icon = portal.icon;
              return (
                <Link
                  key={portal.key}
                  to={`/login?role=${portal.key}`}
                  className="card-shell card-lift fade-up group flex flex-col gap-3 rounded-2xl border border-[var(--border)] bg-white/80 p-5 backdrop-blur transition-all hover:-translate-y-1 hover:shadow-lg hover:shadow-black/5"
                >
                  <div className="flex items-center justify-between">
                    <span className={`grid h-10 w-10 place-items-center rounded-xl ${portal.accent}`}>
                      <Icon className="h-5 w-5" />
                    </span>
                    <ArrowRight className="h-4 w-4 text-[var(--muted-foreground)] opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                  <div>
                    <p className="text-sm font-bold">{portal.title}</p>
                    <p className="mt-1 text-xs text-[var(--muted-foreground)]">{portal.blurb}</p>
                  </div>
                  <ul className="mt-auto flex flex-col gap-1">
                    {portal.features.map((f) => (
                      <li key={f} className="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                        <span className="h-1 w-1 rounded-full bg-[var(--primary)]" /> {f}
                      </li>
                    ))}
                  </ul>
                </Link>
              );
            })}
          </div>
        </section>

        <section className="py-14">
          <h2 className="text-center text-2xl font-bold tracking-tight">Built on transparent AI</h2>
          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {HIGHLIGHTS.map(({ icon: Icon, title, text }) => (
              <div key={title} className="rounded-2xl border border-[var(--border)] bg-white/70 p-5 backdrop-blur">
                <span className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--primary)]/10 text-[var(--primary)]">
                  <Icon className="h-4 w-4" />
                </span>
                <p className="mt-3 text-sm font-bold">{title}</p>
                <p className="mt-1 text-xs text-[var(--muted-foreground)]">{text}</p>
              </div>
            ))}
          </div>
        </section>

        <footer className="flex flex-col items-center gap-1 border-t border-[var(--border)] py-8 text-center">
          <p className="text-sm font-semibold">Beru Campus AI</p>
          <p className="text-xs text-[var(--muted-foreground)]">
            Student · Faculty · Placement · Admin copilots with governance baked in.
          </p>
        </footer>
      </div>
    </div>
  );
}
