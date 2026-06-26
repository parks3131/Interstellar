import type { DriftEvent } from "@/app/lib/types";

export default function ServiceHeatmap({ events }: { events: DriftEvent[] }) {
  const counts: Record<string, number> = {};
  for (const event of events) {
    for (const rs of event.remediation_specs) {
      for (const svc of rs.spec?.affected_services ?? []) {
        counts[svc.service_name] = (counts[svc.service_name] ?? 0) + 1;
      }
    }
  }

  const services = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = services[0]?.[1] ?? 1;

  if (services.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5">
        <h2 className="text-sm font-semibold text-zinc-400 mb-3">Service Drift Heatmap</h2>
        <p className="text-xs text-zinc-600">No affected services recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5">
      <h2 className="text-sm font-semibold text-zinc-400 mb-4">Service Drift Heatmap</h2>
      <div className="space-y-2">
        {services.map(([name, count]) => {
          const pct = Math.round((count / max) * 100);
          const heat = pct >= 80 ? "bg-red-600" : pct >= 50 ? "bg-orange-500" : "bg-yellow-500";
          return (
            <div key={name} className="flex items-center gap-3">
              <span className="text-xs font-mono text-zinc-300 w-32 truncate">{name}</span>
              <div className="flex-1 h-2 rounded bg-zinc-800">
                <div
                  className={`h-2 rounded ${heat} transition-all`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs text-zinc-500 w-4 text-right">{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
