export interface SiteHelpEntry {
  id: string;
  keywords: string[];
  answer: string;
}

const ENTRIES: SiteHelpEntry[] = [
  {
    id: "welcome",
    keywords: ["welcome", "start", "about this website", "about this site", "what is beru", "landing"],
    answer:
      "Beru Campus AI is an autonomous multi-agent university operating system. It brings together a Student Copilot, Faculty Copilot, Placement Copilot and an Admin Command Center in one platform, powered by LangGraph agents, hybrid RAG, and ML-driven predictions. Everything mutating is approval-gated and audited.",
  },
  {
    id: "signin",
    keywords: ["sign in", "signin", "login", "log in", "demo account", "demo accounts", "credentials", "password", "username", "access"],
    answer:
      "You can sign in with one of the seeded demo accounts:\n\n• admin / admin123 (Administrator)\n• lecturer / lecturer123 (Faculty)\n• placement / placement123 (Placement Officer)\n• student / student123 (Student)\n\nThese are created automatically on first boot.",
  },
  {
    id: "logout",
    keywords: ["sign out", "logout", "log out"],
    answer:
      "To sign out, open the sidebar (or the mobile menu) and click the sign-out icon next to your name at the bottom. On mobile there is also a sign-out button in the top bar.",
  },
  {
    id: "navigation",
    keywords: ["navigate", "navigation", "menu", "sidebar", "find a page", "how do i get to", "go to", "route", "breadcrumb"],
    answer:
      "Use the left sidebar to move around the app. It groups pages by area (Overview, Placement, Assistants, Faculty Tools, Insights, Admin Center). You can collapse it, and on mobile it opens from the top-left menu icon. There is also a search box at the top of the sidebar to filter pages by name, and a breadcrumb trail above each page shows where you are.",
  },
  {
    id: "roles",
    keywords: ["role", "roles", "permission", "rbac", "who can", "student vs", "different accounts"],
    answer:
      "The platform has four roles, each with its own area:\n\n• Student — My Space, dashboard, insights, exam prep, assignments, mock interview, resume ATS, project mentor, community.\n• Faculty (lecturer) — Faculty Copilot, course reports, remedial plans, similarity check, audit, and tool suite (question paper, lesson plan, teaching material, assignment evaluation, code review, lab assistant, viva questions).\n• Placement Officer — Placement dashboard, JD analyzer, job–student matching, drives & rounds, gaps & training, company CRM, reports.\n• Administrator — Command Center, user management, departments, approvals, audit, governance, system health, model registry, analytics, timetable optimizer, digital twin, AI Admin Copilot.",
  },
  {
    id: "student",
    keywords: ["student", "my space", "student copilot", "my dashboard", "my insights"],
    answer:
      "The Student area gives each student a success score (0–100) with risk band and drivers, early warnings (attendance below 75%, failing grades, unmet prerequisites), predicted pass probability per course, a daily priority plan, and a personal AI advisor. Check My Space, My Dashboard and My Insights from the sidebar. Exam Prep, Assignment Assistant, Mock Interview, Resume ATS and Project Mentor are under the Assistants section.",
  },
  {
    id: "faculty",
    keywords: ["faculty", "lecturer", "faculty copilot", "workload", "class performance", "course health", "at risk"],
    answer:
      "The Faculty Copilot shows your workload (courses, students, teaching hours), class performance intelligence, an at-risk monitor with explainable reasons, and a course health score with attendance reports. You can also propose interventions — an approval-gated flow where you approve your own interventions and the Execute Agent persists them with an audit trail. Faculty tools (question paper, lesson plan, teaching material, assignment evaluation, code review, lab assistant, viva questions) are under Faculty Tools.",
  },
  {
    id: "placement",
    keywords: ["placement", "jd analyzer", "shortlist", "job student matching", "matching", "drives", "readiness", "unplaced"],
    answer:
      "The Placement Copilot covers a placement readiness score (0–100) with band and components, a batch overview with predicted placement rate and department comparison, an unplaced-risk monitor, AI job–student shortlisting (GPA + backlog gates with match-score ranking), and one-click batch reports. Tools include the JD Analyzer, Drives & Rounds, Gaps & Training and Company CRM.",
  },
  {
    id: "admin",
    keywords: ["admin", "command center", "university health score", "kill switch", "early warning"],
    answer:
      "The Admin Command Center is the platform's control room. It shows counts and KPIs, a University Health Score (0–100 across 5 axes), an Early Warning System (dropout risk, attendance, weak courses, placement readiness), department intelligence, faculty workload analytics, and an Agent Control Center with 7 agents. Admin also gets user management, approvals, the audit center, governance, system health, the AI Admin Copilot, Digital Twin and Timetable Optimizer.",
  },
  {
    id: "assistant",
    keywords: ["ai assistant", "chat", "ask the ai", "supervisor", "agents", "multilingual", "copilot"],
    answer:
      "Open the AI Assistant from the sidebar (Assistants → AI Assistant). It routes your question to a specialist agent (Advising, Success, Resource) via a supervisor. It is propose-only — it never writes to the system without an approved approval request, and every write is recorded in the immutable audit trail. Answers are grounded by RAG and include citations when available.",
  },
  {
    id: "approvals",
    keywords: ["approval", "approve", "reject", "human in the loop", "pending approval", "require approved", "approval request"],
    answer:
      "Beru follows a governance loop: a specialist agent proposes, an approval request is created, and a human (admin or the owning lecturer) approves or rejects it. Only the Execute Agent may write, and it is blocked by the safety kill switch while execution is paused. Each approved write is recorded in the audit log with its approval ID.",
  },
  {
    id: "audit",
    keywords: ["audit", "audit trail", "audit log", "hash chain", "immutable", "history"],
    answer:
      "The audit trail is an immutable, hash-chained log of every mutating operation. Each entry carries the approval ID that authorized the write. You can review it from Faculty → Audit Log (lecturer) or Admin → Audit Center (admin).",
  },
  {
    id: "safety",
    keywords: ["kill switch", "safety", "pause", "read only", "read-only", "stop the ai", "emergency"],
    answer:
      "Admins can use the Emergency Kill Switch from the Command Center. It pauses AI execution or puts the system in read-only mode — the Execute Agent rejects every write at the source while paused. The current status shows on the System Health page.",
  },
  {
    id: "notifications",
    keywords: ["notification", "bell", "alerts", "unread"],
    answer:
      "The bell icon in the top bar shows your notifications. Click it to view alerts, mark individual notifications read, or mark all as read.",
  },
  {
    id: "rag",
    keywords: ["rag", "knowledge base", "grounded", "citations", "curriculum", "evidence", "vector"],
    answer:
      "Answers are grounded by a hybrid RAG pipeline (keyword + vector retrieval). The knowledge base covers the Anna University AIDS Reg 2021 curriculum (229 chunks), and answers carry citations when grounded. If the main RAG finds no evidence or the LLM refuses, the in-process curriculum RAG takes over and answers strictly from its own corpus.",
  },
  {
    id: "ml",
    keywords: ["ml", "machine learning", "prediction", "predict", "dropout risk", "shap", "model", "risk score", "probability"],
    answer:
      "The ML pipeline produces feature datasets and predictions for dropout risk, placement, attendance and performance (heuristic + sklearn models), with SHAP explanations for every prediction. Admins can inspect the Model Registry; risk predictions and explanations appear on student and faculty dashboards. The Timetable Optimizer uses OR-Tools to solve timetable scheduling.",
  },
  {
    id: "timetable",
    keywords: ["timetable", "schedule", "optimizer", "scheduling", "or tools", "or-tools"],
    answer:
      "The Timetable Optimizer (Admin Center → Timetable Optimizer) uses OR-Tools to build collision-free timetables from courses, rooms and constraints.",
  },
  {
    id: "synthetic",
    keywords: ["synthetic", "sample data", "demo data", "generate data", "test data"],
    answer:
      "The platform ships with deterministic synthetic data: 500 students and 40 courses (seed 42). It is seeded on first boot, so every role has data to explore. You can regenerate it from the backend with `python -m synthetic.cli --students 500 --courses 40 --seed 42`.",
  },
  {
    id: "reports",
    keywords: ["report", "reports", "download", "export", "batch report"],
    answer:
      "Reports live in role-specific areas: Placement → Placement Reports gives one-click batch reports, Faculty → Course Reports summarizes performance per course, and Admin has analytics pages for students, faculty, placement, dropout, curriculum, enrollment forecast and accreditation.",
  },
  {
    id: "analytics",
    keywords: ["analytics", "insights", "dashboard", "charts", "kpi"],
    answer:
      "Analytics are available per role: Insights → Analytics for faculty, Placement Analytics in the placement area, and a full analytics suite under Admin Center → (Student/Faculty/Placement/Dropout/Curriculum/Enrollment/Accreditation) Analytics. Dashboards use KPIs, gauges and charts throughout.",
  },
  {
    id: "governance",
    keywords: ["governance", "privacy", "security", "jwt", "bcrypt", "safe", "audited"],
    answer:
      "Security and governance are built in: JWT + bcrypt authentication with role-based access control per route, an approval → execute → audit pipeline for every write, an emergency kill switch, and a secure-boot guard that refuses production boots with default credentials.",
  },
];

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

export function findSiteHelp(question: string): SiteHelpEntry | null {
  const q = question.trim().toLowerCase();
  const tokens = new Set(tokenize(q));
  if (tokens.size === 0) return null;

  let best: SiteHelpEntry | null = null;
  let bestScore = 0;
  let secondScore = 0;

  for (const entry of ENTRIES) {
    let score = 0;
    for (const keyword of entry.keywords) {
      const kwTokens = tokenize(keyword);
      if (kwTokens.length > 0 && kwTokens.every((t) => tokens.has(t))) {
        score += kwTokens.length;
      } else if (kwTokens.length === 1 && q.includes(kwTokens[0])) {
        score += 1;
      }
    }
    if (score > bestScore) {
      secondScore = bestScore;
      bestScore = score;
      best = entry;
    } else if (score > secondScore) {
      secondScore = score;
    }
  }

  if (bestScore >= 2) return best;
  if (bestScore === 1 && secondScore === 0) return best;
  return null;
}

export const HELP_TOPICS = [
  "How do I sign in?",
  "What can students do?",
  "How do approvals work?",
  "Where is the audit log?",
  "What is the AI Assistant?",
  "What does the Command Center show?",
];

export const HELP_FALLBACK =
  "I'm the Beru site assistant. I can help you navigate this platform — ask about demo accounts, roles, features, approvals, the audit trail, or how to find a page. If you're signed in, I can also pass your question to the main AI Assistant.";
