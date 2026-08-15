import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, ClipboardCheck, GraduationCap, ThumbsUp } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/core/components/PageHeader";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { useAuthStore } from "@/core/stores/auth";
import { adminApi, type EvaluationResult } from "@/modules/admin/api";

const gradeStyles: Record<string, string> = {
  "A+": "bg-green-100 text-green-700",
  A: "bg-emerald-100 text-emerald-700",
  B: "bg-sky-100 text-sky-700",
  C: "bg-amber-100 text-amber-700",
  D: "bg-orange-100 text-orange-700",
  F: "bg-red-100 text-red-700",
};

const SAMPLE = {
  course_code: "CS101",
  question: "Explain binary trees and their use cases.",
  rubric: "Clarity: clear expression of ideas\nDepth: thorough analysis of the topic\nExamples: relevant real-world examples",
  max_marks: 100,
  answer:
    "A binary tree is a hierarchical data structure where each node has at most two children, the left and right child. " +
    "It supports efficient search, insertion and deletion operations. Balanced variants like AVL and red-black trees " +
    "guarantee O(log n) time complexity for these operations. Binary trees are used in compilers for expression parsing, " +
    "in databases for indexing (B-trees are a generalization), and in routers for packet classification.",
};

export function AdminEvaluationCenter() {
  const token = useAuthStore((s) => s.token);
  const [course, setCourse] = useState("");
  const [question, setQuestion] = useState("");
  const [rubric, setRubric] = useState("");
  const [maxMarks, setMaxMarks] = useState(100);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [error, setError] = useState("");

  const evaluate = useMutation({
    mutationFn: () =>
      adminApi.evaluate(
        { course_code: course || undefined, question, rubric: rubric || undefined, answer, max_marks: maxMarks },
        token!
      ),
    onSuccess: (r) => {
      setResult(r);
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });

  const loadSample = () => {
    setCourse(SAMPLE.course_code);
    setQuestion(SAMPLE.question);
    setRubric(SAMPLE.rubric);
    setMaxMarks(SAMPLE.max_marks);
    setAnswer(SAMPLE.answer);
  };

  const canRun = question.trim() && answer.trim();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="AI Evaluation Center"
        subtitle="Rubric-based grading of answers with structured feedback"
        icon={ClipboardCheck}
        actions={
          <Button variant="outline" onClick={loadSample}>
            Load sample
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Evaluate answer</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
              Course code
              <Input value={course} onChange={(e) => setCourse(e.target.value)} placeholder="CS101" />
            </label>
            <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
              Question
              <Input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Explain…" />
            </label>
            <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
              Max marks
              <Input type="number" value={maxMarks} onChange={(e) => setMaxMarks(Number(e.target.value))} />
            </label>
          </div>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Rubric (one criterion per line: `Name: description`)
            <textarea
              value={rubric}
              onChange={(e) => setRubric(e.target.value)}
              rows={3}
              placeholder="Clarity: clear expression of ideas&#10;Depth: thorough analysis"
              className="rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)]"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-[var(--muted-foreground)]">
            Student answer
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={6}
              placeholder="Paste the answer here…"
              className="rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)]"
            />
          </label>
          <div className="flex items-center gap-3">
            <Button disabled={!canRun || evaluate.isPending} onClick={() => evaluate.mutate()}>
              <GraduationCap className="h-4 w-4" /> Evaluate
            </Button>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-3">
              Result — {result.question}
              <span className={`rounded-full px-3 py-0.5 text-sm font-bold ${gradeStyles[result.grade] ?? "bg-[var(--muted)]"}`}>
                {result.grade}
              </span>
              <span className="text-[var(--muted-foreground)]">
                {result.total_marks} / {result.max_marks}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                  <th className="pb-2">Criterion</th>
                  <th className="pb-2 text-right">Marks</th>
                  <th className="pb-2">Comment</th>
                </tr>
              </thead>
              <tbody>
                {result.criteria.map((c) => (
                  <tr key={c.name} className="border-b border-[var(--border)]">
                    <td className="py-2 font-medium">{c.name}</td>
                    <td className="py-2 text-right">{c.marks} / {c.max}</td>
                    <td className="py-2 text-[var(--muted-foreground)]">{c.comment}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p className="text-sm leading-relaxed">{result.feedback}</p>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <p className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-green-700">
                  <ThumbsUp className="h-3.5 w-3.5" /> Strengths
                </p>
                <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
                  {result.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Improvements
                </p>
                <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
                  {result.improvements.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            </div>

            <p className="text-xs text-[var(--muted-foreground)]">engine: {result.provider}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
