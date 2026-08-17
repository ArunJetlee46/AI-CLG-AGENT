import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  AlertCircle,
  Award,
  BookOpen,
  CheckCircle2,
  Clock,
  Flag,
  GraduationCap,
  HelpCircle,
  Loader2,
  RefreshCw,
  Target,
  TrendingUp,
  XCircle,
} from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Progress } from "@/core/components/ui/progress";
import { Separator } from "@/core/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/core/components/ui/tabs";
import { api } from "@/core/lib/api";
import { useAuthStore } from "@/core/stores/auth";
import { cn } from "@/core/lib/utils";

interface DegreeAudit {
  student_id: string;
  program: string;
  credits_required: number;
  credits_earned: number;
  credits_in_progress: number;
  projected_credits: number;
  progress_percentage: number;
  projected_percentage: number;
  gpa: number;
  min_gpa_required: number;
  gpa_met: boolean;
  core_courses: {
    required: string[];
    completed: string[];
    in_progress: string[];
    remaining: string[];
    completion_percentage: number;
    credits_earned: number;
  };
  elective_credits: number;
  current_courses: { course_code: string; title: string; credits: number; status: string }[];
  failed_courses: { course_code: string; title: string; credits: number; marks: number; grade: string }[];
  status: string;
  can_graduate: boolean;
}

const STATUS_CONFIG = {
  ready_to_graduate: { label: "Ready to Graduate", color: "success", icon: Award, desc: "All requirements met" },
  on_track: { label: "On Track", color: "default", icon: Flag, desc: "Projected to meet all requirements" },
  progressing: { label: "Progressing", color: "default", icon: TrendingUp, desc: "Making good progress" },
  at_risk: { label: "At Risk", color: "destructive", icon: AlertCircle, desc: "May not meet requirements on time" },
} as const;

export function DegreeAudit() {
  const token = useAuthStore((s) => s.token);
  const [activeTab, setActiveTab] = useState("overview");

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["degree-audit"],
    queryFn: () => api<DegreeAudit>("/degree-audit/me", {}, token!),
    enabled: !!token,
  });

  const statusConfig = data ? STATUS_CONFIG[data.status as keyof typeof STATUS_CONFIG] : null;
  const StatusIcon = statusConfig?.icon || HelpCircle;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-[var(--primary)]" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card className="card-shell">
        <CardContent className="flex flex-col items-center justify-center gap-4 p-8 text-center">
          <XCircle className="h-12 w-12 text-red-500" />
          <p className="text-lg font-semibold">Unable to load degree audit</p>
          <p className="text-sm text-[var(--muted-foreground)]">Student profile may not be linked</p>
          <Button onClick={() => refetch()} variant="outline">
            <RefreshCw className="mr-1.5 h-4 w-4" /> Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Degree Audit"
        subtitle={`Track your progress toward ${data.program} graduation`}
        icon={GraduationCap}
        accent="bg-indigo-100 text-indigo-600"
        actions={
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-1.5 h-4 w-4" /> Refresh
          </Button>
        }
      />

      {/* Status Banner */}
      <Card className={cn("card-shell border-l-4", statusConfig?.color === "success" && "border-l-emerald-500", statusConfig?.color === "destructive" && "border-l-red-500")}>
        <CardContent className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4">
          <div className="flex items-center gap-3">
            <div className={cn("grid h-12 w-12 place-items-center rounded-xl", statusConfig?.color === "success" && "bg-emerald-100 text-emerald-600", statusConfig?.color === "destructive" && "bg-red-100 text-red-600", statusConfig?.color === "default" && "bg-sky-100 text-sky-600")}>
              <StatusIcon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-lg font-bold">{statusConfig?.label || "Unknown"}</p>
              <p className="text-sm text-[var(--muted-foreground)]">{statusConfig?.desc || ""}</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <Badge tone="outline" className={cn(data.gpa_met ? "text-emerald-600 border-emerald-600" : "text-red-600 border-red-600")}>
              GPA: {data.gpa.toFixed(2)} / {data.min_gpa_required}
            </Badge>
            <Badge tone="outline" className={data.can_graduate ? "text-emerald-600 border-emerald-600" : "text-sky-600 border-sky-600"}>
              {data.can_graduate ? "Eligible to Graduate" : "In Progress"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Progress Overview */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="card-shell">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-[var(--muted-foreground)]">Overall Progress</p>
              <p className="text-sm font-semibold">{data.progress_percentage}%</p>
            </div>
            <Progress value={data.progress_percentage} className="h-3" />
            <p className="text-xs text-[var(--muted-foreground)] mt-1">
              {data.credits_earned} / {data.credits_required} credits earned
            </p>
          </CardContent>
        </Card>

        <Card className="card-shell">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-[var(--muted-foreground)]">Projected (with current courses)</p>
              <p className="text-sm font-semibold text-sky-600">{data.projected_percentage}%</p>
            </div>
            <Progress value={data.projected_percentage} className="h-3" />
            <p className="text-xs text-[var(--muted-foreground)] mt-1">
              +{data.credits_in_progress} in progress = {data.projected_credits} projected
            </p>
          </CardContent>
        </Card>

        <Card className="card-shell">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-[var(--muted-foreground)]">Core Courses</p>
              <p className="text-sm font-semibold">{data.core_courses.completion_percentage}%</p>
            </div>
            <Progress value={data.core_courses.completion_percentage} className="h-3" />
            <p className="text-xs text-[var(--muted-foreground)] mt-1">
              {data.core_courses.completed.length} / {data.core_courses.required.length} completed
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="core">Core Courses</TabsTrigger>
          <TabsTrigger value="current">Current Courses</TabsTrigger>
          <TabsTrigger value="issues">Issues & Actions</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card className="card-shell">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <BookOpen className="h-4 w-4" /> Credit Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span>Credits Required</span>
                  <span className="font-semibold">{data.credits_required}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Credits Earned</span>
                  <span className="font-semibold text-emerald-600">{data.credits_earned}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>In Progress</span>
                  <span className="font-semibold text-sky-600">{data.credits_in_progress}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span>Projected Total</span>
                  <span className="font-semibold">{data.projected_credits}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Core Credits Earned</span>
                  <span className="font-semibold">{data.core_courses.credits_earned}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Elective Credits</span>
                  <span className="font-semibold">{data.elective_credits}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="card-shell">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Target className="h-4 w-4" /> GPA Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span>Current GPA</span>
                  <span className="font-semibold">{data.gpa.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Minimum Required</span>
                  <span className="font-semibold">{data.min_gpa_required}</span>
                </div>
                <Separator />
                <div className="flex items-center gap-2">
                  {data.gpa_met ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" />
                  )}
                  <span className={data.gpa_met ? "text-emerald-600" : "text-red-600"}>
                    {data.gpa_met ? "GPA Requirement Met" : "GPA Below Minimum"}
                  </span>
                </div>
                {!data.gpa_met && (
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Need {data.min_gpa_required - data.gpa > 0 ? (data.min_gpa_required - data.gpa).toFixed(2) : "0.00"} more GPA points
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="core" className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {/* Completed */}
            <Card className="card-shell">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  Completed ({data.core_courses.completed.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 max-h-64 overflow-y-auto">
                  {data.core_courses.completed.map((code) => (
                    <li key={code} className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 px-3 py-2 rounded-lg">
                      <CheckCircle2 className="h-4 w-4" />
                      <span className="font-mono">{code}</span>
                    </li>
                  ))}
                  {data.core_courses.completed.length === 0 && (
                    <li className="text-center text-sm text-[var(--muted-foreground)] py-4">No core courses completed yet</li>
                  )}
                </ul>
              </CardContent>
            </Card>

            {/* In Progress */}
            <Card className="card-shell">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Clock className="h-4 w-4 text-sky-600" />
                  In Progress ({data.core_courses.in_progress.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 max-h-64 overflow-y-auto">
                  {data.core_courses.in_progress.map((code) => (
                    <li key={code} className="flex items-center gap-2 text-sm text-sky-700 bg-sky-50 px-3 py-2 rounded-lg">
                      <Clock className="h-4 w-4" />
                      <span className="font-mono">{code}</span>
                    </li>
                  ))}
                  {data.core_courses.in_progress.length === 0 && (
                    <li className="text-center text-sm text-[var(--muted-foreground)] py-4">No core courses in progress</li>
                  )}
                </ul>
              </CardContent>
            </Card>

            {/* Remaining */}
            <Card className="card-shell">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <AlertCircle className="h-4 w-4 text-amber-600" />
                  Remaining ({data.core_courses.remaining.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 max-h-64 overflow-y-auto">
                  {data.core_courses.remaining.map((code) => (
                    <li key={code} className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
                      <AlertCircle className="h-4 w-4" />
                      <span className="font-mono">{code}</span>
                    </li>
                  ))}
                  {data.core_courses.remaining.length === 0 && (
                    <li className="text-center text-sm text-emerald-600 py-4">All core courses completed!</li>
                  )}
                </ul>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="current" className="space-y-4">
          <Card className="card-shell">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <BookOpen className="h-4 w-4" /> Current Semester Courses
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data.current_courses.length === 0 ? (
                <p className="text-center text-[var(--muted-foreground)] py-8">No current courses found</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                        <th className="py-2 pr-4">Course</th>
                        <th className="py-2 pr-4">Title</th>
                        <th className="py-2 pr-4">Credits</th>
                        <th className="py-2 pr-4">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.current_courses.map((course) => (
                        <tr key={course.course_code} className="border-b border-[var(--border)]">
                          <td className="py-2 pr-4 font-mono font-medium">{course.course_code}</td>
                          <td className="py-2 pr-4">{course.title}</td>
                          <td className="py-2 pr-4">{course.credits}</td>
                          <td className="py-2 pr-4">
                            <Badge tone={data.core_courses.required.includes(course.course_code) ? "default" : "outline"}>
                              {data.core_courses.required.includes(course.course_code) ? "Core" : "Elective"}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="issues" className="space-y-4">
          {data.failed_courses.length > 0 && (
            <Card className="card-shell border-l-4 border-l-red-500">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <XCircle className="h-4 w-4 text-red-600" />
                  Failed Courses ({data.failed_courses.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-[var(--muted-foreground)] mb-3">
                  These courses need to be retaken. Contact your faculty advisor for retake options.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                        <th className="py-2 pr-4">Course</th>
                        <th className="py-2 pr-4">Title</th>
                        <th className="py-2 pr-4">Credits</th>
                        <th className="py-2 pr-4">Marks</th>
                        <th className="py-2 pr-4">Grade</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.failed_courses.map((course) => (
                        <tr key={course.course_code} className="border-b border-[var(--border)] bg-red-50">
                          <td className="py-2 pr-4 font-mono font-medium">{course.course_code}</td>
                          <td className="py-2 pr-4">{course.title}</td>
                          <td className="py-2 pr-4">{course.credits}</td>
                          <td className="py-2 pr-4">{course.marks}</td>
                          <td className="py-2 pr-4"><span className="text-red-600 font-medium">{course.grade}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {data.core_courses.remaining.length > 0 && (
            <Card className="card-shell border-l-4 border-l-amber-500">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <AlertCircle className="h-4 w-4 text-amber-600" />
                  Remaining Core Requirements ({data.core_courses.remaining.length} courses)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-[var(--muted-foreground)] mb-3">
                  Plan to take these courses in upcoming semesters. Check prerequisites before registering.
                </p>
                <ul className="flex flex-wrap gap-2">
                  {data.core_courses.remaining.map((code) => (
                    <li key={code} className="px-3 py-1.5 text-sm bg-amber-50 text-amber-700 rounded-lg font-mono">
                      {code}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {!data.gpa_met && (
            <Card className="card-shell border-l-4 border-l-red-500">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Target className="h-4 w-4 text-red-600" />
                  GPA Improvement Needed
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-[var(--muted-foreground)]">
                  Current GPA: <strong>{data.gpa.toFixed(2)}</strong> | Required: <strong>{data.min_gpa_required}</strong>
                </p>
                <p className="text-sm text-[var(--muted-foreground)] mt-2">
                  Focus on improving grades in current and upcoming courses. Consider tutoring for challenging subjects.
                </p>
              </CardContent>
            </Card>
          )}

          {data.failed_courses.length === 0 && data.core_courses.remaining.length === 0 && data.gpa_met && (
            <Card className="card-shell border-l-4 border-l-emerald-500">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  No Issues Found
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-emerald-700">
                  All requirements are on track. Keep up the excellent work!
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}