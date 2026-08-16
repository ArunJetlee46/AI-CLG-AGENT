import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { BookOpen, CheckCircle2, RefreshCw } from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { cn } from "@/core/lib/utils";
import { studentApi, type QuizQuestion } from "@/modules/student/api";
import { useAuthStore } from "@/core/stores/auth";

export function ExamPrep() {
  const token = useAuthStore((s) => s.token);
  const [courseCode, setCourseCode] = useState("AD3301");
  const [generated, setGenerated] = useState("");
  const [selected, setSelected] = useState<Record<string, number>>({});
  const [revealed, setRevealed] = useState<string[]>([]);

  const quiz = useQuery({
    queryKey: ["exam-prep", generated],
    queryFn: () => studentApi.examPrep(token!, generated || "AD3301", 5),
    enabled: !!token && generated.length > 0,
  });

  const generate = () => {
    if (!courseCode.trim()) return;
    setSelected({});
    setRevealed([]);
    setGenerated(courseCode.trim().toUpperCase());
  };

  const correct = (q: QuizQuestion) => selected[q.id] === q.answer_index;
  const score = quiz.data?.questions.filter((q) => revealed.includes(q.id) && correct(q)).length ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Exam Prep" subtitle="AI-generated practice questions with answers and explanations" icon={BookOpen} accent="bg-teal-100 text-teal-600" />

      <Card className="card-shell">
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-[var(--muted-foreground)]">Course code</label>
            <Input
              value={courseCode}
              onChange={(e) => setCourseCode(e.target.value.toUpperCase())}
              placeholder="e.g. AD3301"
              className="w-48"
            />
          </div>
          <Button disabled={!courseCode.trim() || quiz.isFetching} onClick={generate}>
            <RefreshCw className={cn("mr-1.5 h-4 w-4", quiz.isFetching && "animate-spin")} /> Generate
          </Button>
          {quiz.data && (
            <Badge tone="neutral" className="ml-auto">
              {quiz.data.provider} · {quiz.data.questions.length} questions · {score}/{revealed.length} correct
            </Badge>
          )}
        </CardContent>
      </Card>

      {quiz.data?.questions.map((q) => (
        <Card key={q.id} className="card-shell">
          <CardHeader>
            <CardTitle className="text-sm font-semibold">
              <span className="font-mono text-xs text-[var(--muted-foreground)]">{q.course_code} · Q{q.id.slice(1)}</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="text-sm">{q.question}</p>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {q.options.map((opt, idx) => {
                const isSelected = selected[q.id] === idx;
                const isCorrect = idx === q.answer_index;
                const isRevealed = revealed.includes(q.id);
                return (
                  <button
                    key={idx}
                    disabled={isRevealed}
                    onClick={() => setSelected((s) => ({ ...s, [q.id]: idx }))}
                    className={cn(
                      "rounded-lg border px-3 py-2 text-left text-sm transition-colors",
                      isSelected && "border-[var(--primary)] bg-[var(--primary)]/5",
                      isRevealed && isCorrect && "border-emerald-500 bg-emerald-50 text-emerald-800",
                      isRevealed && isSelected && !isCorrect && "border-red-500 bg-red-50 text-red-800",
                      !isRevealed && "border-[var(--border)] hover:bg-[var(--muted)]"
                    )}
                  >
                    <span className="mr-1.5 font-mono text-xs text-[var(--muted-foreground)]">{String.fromCharCode(97 + idx)})</span>
                    {opt}
                  </button>
                );
              })}
            </div>
            {!revealed.includes(q.id) ? (
              <div>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={selected[q.id] === undefined}
                  onClick={() => setRevealed((r) => [...r, q.id])}
                >
                  <CheckCircle2 className="mr-1.5 h-4 w-4" /> Check answer
                </Button>
              </div>
            ) : (
              <div className={cn("rounded-lg border-l-4 px-3 py-2 text-sm", correct(q) ? "border-emerald-500 bg-emerald-50" : "border-red-500 bg-red-50")}>
                <span className="font-semibold">{correct(q) ? "Correct." : "Not quite."}</span> {q.explanation}
              </div>
            )}
          </CardContent>
        </Card>
      ))}

      {!quiz.data && !quiz.isFetching && quiz.isError && (
        <p className="text-center text-sm text-[var(--muted-foreground)]">Could not load questions for that course. Try a different course code.</p>
      )}
      {!quiz.data && !quiz.isFetching && !quiz.isError && (
        <p className="text-center text-sm text-[var(--muted-foreground)]">Enter a course code and press Generate to start a quiz.</p>
      )}
      {quiz.isFetching && <p className="text-center text-sm text-[var(--muted-foreground)]">Generating questions…</p>}
    </div>
  );
}
