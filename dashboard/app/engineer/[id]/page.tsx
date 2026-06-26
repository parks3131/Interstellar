import Link from "next/link";
import type { EngineerGraph, Severity } from "@/app/lib/types";

const SEVERITY_STYLES: Record<Severity, string> = {
  CRITICAL: "bg-purple-900/50 text-purple-300 border border-purple-700",
  HIGH: "bg-red-900/50 text-red-300 border border-red-700",
  LOW: "bg-yellow-900/50 text-yellow-300 border border-yellow-700",
  NONE: "bg-zinc-800 text-zinc-400 border border-zinc-700",
};

async function getEngineer(id: string): Promise<EngineerGraph | null> {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/graph/engineer/${encodeURIComponent(id)}`,
    { cache: "no-store" }
  );
  if (!res.ok) return null;
  return res.json();
}

export default async function EngineerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const engineer = await getEngineer(id);

  if (!engineer) {
    return (
      <main className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-400">Engineer &quot;{id}&quot; not found in graph.</p>
          <Link href="/" className="text-blue-400 text-sm mt-3 block hover:text-blue-300">
            ← Back to feed
          </Link>
        </div>
      </main>
    );
  }

  const totalDrifts = engineer.pull_requests.filter(
    (pr) => pr.drift_events.length > 0
  ).length;

  return (
    <main className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="mb-2">
          <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
            ← Back
          </Link>
        </div>

        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight">@{engineer.engineer_name}</h1>
          <p className="text-sm text-zinc-400 mt-1">
            {engineer.pull_requests.length} PR{engineer.pull_requests.length !== 1 ? "s" : ""} ·{" "}
            {totalDrifts} drift{totalDrifts !== 1 ? "s" : ""}
          </p>
        </div>

        <div className="flex flex-col gap-4">
          {engineer.pull_requests.map((pr) => {
            const hasDrift = pr.drift_events.length > 0;
            const topSeverity = pr.drift_events[0]?.severity;
            return (
              <div
                key={pr.pr_number}
                className="rounded-lg border border-zinc-800 bg-zinc-900 p-5"
              >
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-mono text-zinc-200">PR #{pr.pr_number}</span>
                    {pr.jira_key && (
                      <>
                        <span className="text-xs text-zinc-500">·</span>
                        <span className="text-xs font-mono text-zinc-400">{pr.jira_key}</span>
                      </>
                    )}
                    {hasDrift && topSeverity && (
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded ${SEVERITY_STYLES[topSeverity]}`}>
                        {topSeverity}
                      </span>
                    )}
                    {!hasDrift && (
                      <span className="text-xs px-2 py-0.5 rounded bg-green-900/40 text-green-400 border border-green-800">
                        Aligned
                      </span>
                    )}
                  </div>
                </div>

                {pr.pr_title && (
                  <p className="text-sm text-zinc-300 mb-2">{pr.pr_title}</p>
                )}

                {pr.drifted_services.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {pr.drifted_services.map((svc) => (
                      <span key={svc} className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono">
                        {svc}
                      </span>
                    ))}
                  </div>
                )}

                {pr.drift_events.map((de) => (
                  <p key={de.id} className="text-xs text-zinc-500 leading-relaxed">
                    {de.reasoning}
                  </p>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </main>
  );
}
