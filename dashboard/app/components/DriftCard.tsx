import Link from "next/link";
import type { DriftEvent, Severity } from "@/app/lib/types";
import AcknowledgeButton from "./AcknowledgeButton";

const SEVERITY_STYLES: Record<Severity, string> = {
  CRITICAL: "bg-purple-900/50 text-purple-300 border border-purple-700",
  HIGH: "bg-red-900/50 text-red-300 border border-red-700",
  LOW: "bg-yellow-900/50 text-yellow-300 border border-yellow-700",
  NONE: "bg-zinc-800 text-zinc-400 border border-zinc-700",
};

export default function DriftCard({ event }: { event: DriftEvent }) {
  const spec = event.remediation_specs[0]?.spec;
  const specStatus = event.remediation_specs[0]?.status ?? "open";
  const specId = event.remediation_specs[0]?.id;
  const affectedServices = spec?.affected_services ?? [];
  const owner = spec?.owner;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 flex flex-col gap-3 hover:border-zinc-700 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-semibold px-2 py-0.5 rounded ${SEVERITY_STYLES[event.severity]}`}>
            {event.severity}
          </span>
          <span className="text-sm font-mono text-zinc-300">
            PR #{event.pr_number}
          </span>
          <span className="text-xs text-zinc-500">·</span>
          <span className="text-xs text-zinc-400 font-mono">{event.jira_key}</span>
          <span className="text-xs text-zinc-500">·</span>
          <span className="text-xs text-zinc-500">{event.repo}</span>
        </div>
        <span className="text-xs text-zinc-600 whitespace-nowrap">
          {new Date(event.created_at).toLocaleDateString("en-US", {
            month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
          })}
        </span>
      </div>

      <p className="text-sm text-zinc-300 leading-relaxed">{event.reasoning}</p>

      {spec && (
        <div className="rounded bg-zinc-800/60 border border-zinc-700/50 p-3 text-xs text-zinc-400 space-y-1">
          <p className="text-zinc-300">{spec.summary}</p>
          {affectedServices.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {affectedServices.map((svc) => (
                <span key={svc.service_name} className="px-1.5 py-0.5 rounded bg-zinc-700 text-zinc-300 font-mono">
                  {svc.service_name}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-3">
          {owner && (
            <Link
              href={`/engineer/gh_${owner}`}
              className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              @{owner}
            </Link>
          )}
          {spec && (
            <span className="text-xs text-zinc-500">
              → {spec.action_required.replace(/_/g, " ")}
            </span>
          )}
        </div>
        {specId != null && (
          <AcknowledgeButton driftEventId={event.id} initialStatus={specStatus} />
        )}
      </div>
    </div>
  );
}
