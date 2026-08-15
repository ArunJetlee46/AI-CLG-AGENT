import { ClipboardCheck, Code2, FileText, FlaskConical, ListChecks, Presentation, TestTube2, Wrench } from "lucide-react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/core/components/PageHeader";

const TOOLS = [
  { to: "/faculty/tools/question-paper", label: "Question Paper", desc: "Generate balanced exam papers by topic, difficulty and question count.", icon: FileText, accent: "bg-violet-100 text-violet-600" },
  { to: "/faculty/tools/lesson-plan", label: "Lesson Plan", desc: "Timed session structures with learning outcomes and assessment.", icon: Presentation, accent: "bg-sky-100 text-sky-600" },
  { to: "/faculty/tools/teaching-material", label: "Teaching Material", desc: "Notes, slides or outlines for any topic.", icon: Wrench, accent: "bg-emerald-100 text-emerald-600" },
  { to: "/faculty/tools/assignment-eval", label: "Assignment Evaluation", desc: "Score submissions against your rubric with feedback.", icon: ClipboardCheck, accent: "bg-amber-100 text-amber-600" },
  { to: "/faculty/tools/code-review", label: "Code Review", desc: "Review student code for quality, correctness and safety.", icon: Code2, accent: "bg-red-100 text-red-600" },
  { to: "/faculty/tools/lab-assistant", label: "Lab Assistant", desc: "Step-by-step, safety-aware lab guidance.", icon: FlaskConical, accent: "bg-orange-100 text-orange-600" },
  { to: "/faculty/tools/viva-questions", label: "Viva Questions", desc: "Understanding-focused viva voce question banks.", icon: TestTube2, accent: "bg-pink-100 text-pink-600" },
];

export function FacultyTools() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Faculty Tools" subtitle="Question papers, lesson plans, material, evaluation, code review, lab and viva" icon={ListChecks} accent="bg-violet-100 text-violet-600" />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {TOOLS.map(({ to, label, desc, icon: Icon, accent }) => (
          <Link
            key={to}
            to={to}
            className="group flex flex-col gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
          >
            <span className={`grid h-11 w-11 place-items-center rounded-xl ${accent}`}>
              <Icon className="h-5 w-5" />
            </span>
            <div>
              <p className="font-semibold">{label}</p>
              <p className="mt-1 text-sm text-[var(--muted-foreground)]">{desc}</p>
            </div>
            <span className="mt-auto text-sm font-medium text-[var(--primary)] opacity-0 transition-opacity group-hover:opacity-100">
              Open tool →
            </span>
          </Link>
        ))}
      </div>

      <p className="rounded-lg border-l-4 border-[var(--primary)] bg-[var(--primary)]/5 px-3 py-2 text-sm">
        Tools are LLM-first through the campus gateway and fall back to deterministic templates when the model is unreachable.
      </p>
    </div>
  );
}
