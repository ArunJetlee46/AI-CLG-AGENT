import { useQuery } from "@tanstack/react-query";
import { TrendingUp } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PageHeader } from "@/core/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { predictionApi, type TaskPredictionRow } from "@/core/lib/api";
import { useAuthStore } from "@/core/stores/auth";

const TASK_LABELS: Record<string, keyof TaskPredictionRow & string> = {
  performance: "pass_probability",
  placement: "placement_probability",
  attendance: "absence_risk",
  dropout: "dropout_probability",
};

const RISK_ORDER = ["low", "medium", "high"];

export function AnalyticsDashboard() {
  const token = useAuthStore((s) => s.token);

  const all = useQuery({
    queryKey: ["predictions-all"],
    queryFn: () => predictionApi.all(token!, 100),
    enabled: !!token,
  });

  const rows = all.data ?? [];
  const tasks = Object.keys(TASK_LABELS);

  const chartData = tasks.map((task) => {
    const group = rows.filter((r) => r.task === task);
    const key = TASK_LABELS[task];
    const counts = RISK_ORDER.reduce<Record<string, number>>((acc, level) => ({ ...acc, [level]: 0 }), {});
    group.forEach((r) => {
      counts[r.risk_level] = (counts[r.risk_level] ?? 0) + 1;
    });
    return {
      task,
      ...counts,
      total: group.length,
      avg:
        group.length > 0
          ? Math.round((group.reduce((s, r) => s + Number(r[key] ?? 0), 0) / group.length) * 100)
          : 0,
    };
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Analytics Dashboard"
        subtitle="Risk distribution across all four ML tasks"
        icon={TrendingUp}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Risk levels by task</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="task" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="low" stackId="a" fill="#22c55e" />
                <Bar dataKey="medium" stackId="a" fill="#f59e0b" />
                <Bar dataKey="high" stackId="a" fill="#ef4444" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Average score by task</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="task" />
                <YAxis unit="%" domain={[0, 100]} />
                <Tooltip />
                <Bar dataKey="avg" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent predictions</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                <th className="pb-2">Student</th>
                <th className="pb-2">Task</th>
                <th className="pb-2">Score</th>
                <th className="pb-2">Risk</th>
                <th className="pb-2">Key driver</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 20).map((r, i) => {
                const key = TASK_LABELS[r.task];
                const driver = Object.entries(r.contributions ?? {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0];
                return (
                  <tr key={`${r.student_id}-${r.task}-${i}`} className="border-b border-[var(--border)]">
                    <td className="py-2">{r.student_id}</td>
                    <td className="py-2">{r.task}</td>
                    <td className="py-2">{Math.round(Number(r[key] ?? 0) * 100)}%</td>
                    <td className="py-2">{r.risk_level}</td>
                    <td className="py-2 text-xs text-[var(--muted-foreground)]">
                      {driver ? `${driver[0]}: ${Number(driver[1]).toFixed(3)}` : "-"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.length === 0 && (
            <p className="text-sm text-[var(--muted-foreground)]">
              No predictions yet. Seed the DB (synthetic generator), train models, then re-visit.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
