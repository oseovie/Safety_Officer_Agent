import { AlertTriangle, BadgeCheck, ClipboardCheck, FileText, ShieldCheck } from "lucide-react";
import type { DashboardData } from "@/lib/api";

const levelStyles: Record<string, string> = {
  low: "bg-emerald-500",
  medium: "bg-amber-500",
  high: "bg-orange-600",
  critical: "bg-red-600"
};

export function Dashboard({ data }: { data: DashboardData }) {
  const total = Object.values(data.hazards_by_level).reduce((sum, value) => sum + value, 0) || 1;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <section className="border-b bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-6 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">SentinelSafe</p>
            <h1 className="mt-1 text-3xl font-semibold">Safety Operations Command Center</h1>
          </div>
          <div className="flex gap-2">
            <button className="inline-flex h-10 items-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-medium text-white">
              <ClipboardCheck size={18} /> New Inspection
            </button>
            <button className="inline-flex h-10 items-center gap-2 rounded-md border bg-white px-4 text-sm font-medium">
              <FileText size={18} /> Export Pack
            </button>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-4 px-5 py-6 md:grid-cols-4">
        <Metric icon={<AlertTriangle />} label="Open Hazards" value={data.metrics.open_hazards} />
        <Metric icon={<ShieldCheck />} label="Open Actions" value={data.metrics.open_actions} />
        <Metric icon={<AlertTriangle />} label="Critical Hazards" value={data.metrics.critical_hazards} />
        <Metric icon={<BadgeCheck />} label="Avg. Risk Score" value={data.metrics.average_risk_score} />
      </section>

      <section className="mx-auto grid max-w-7xl gap-5 px-5 pb-8 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Risk Distribution</h2>
            <span className="text-sm text-slate-500">Live tenant scope</span>
          </div>
          <div className="mt-6 space-y-4">
            {Object.entries(data.hazards_by_level).map(([level, count]) => (
              <div key={level}>
                <div className="mb-2 flex justify-between text-sm">
                  <span className="capitalize">{level}</span>
                  <span>{count}</span>
                </div>
                <div className="h-3 overflow-hidden rounded bg-slate-100">
                  <div className={`h-full ${levelStyles[level]}`} style={{ width: `${(count / total) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold">AI Risk Insights</h2>
          <div className="mt-4 space-y-3">
            {data.risk_insights.map((insight) => (
              <p className="rounded-md border-l-4 border-emerald-600 bg-emerald-50 px-3 py-2 text-sm" key={insight}>
                {insight}
              </p>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between text-slate-500">
        <span className="text-sm font-medium">{label}</span>
        <span className="[&>svg]:h-5 [&>svg]:w-5">{icon}</span>
      </div>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
    </div>
  );
}
