export type Severity = "NONE" | "LOW" | "HIGH" | "CRITICAL";

export interface AffectedService {
  service_name: string;
  action: string;
  reason: string;
}

export interface RemediationSpecBody {
  owner: string;
  summary: string;
  jira_key: string;
  severity: Severity;
  pr_number: number;
  action_required: string;
  affected_services: AffectedService[];
  suggested_pr_description: string;
}

export interface RemediationSpec {
  id: number;
  spec: RemediationSpecBody;
  status: "open" | "acknowledged";
  created_at: string;
  drift_event_id: number;
}

export interface DriftEvent {
  id: number;
  pr_number: number;
  jira_key: string;
  severity: Severity;
  reasoning: string;
  repo: string;
  created_at: string;
  remediation_specs: RemediationSpec[];
}

export interface EngineerPR {
  pr_number: number;
  pr_title: string;
  repo: string;
  jira_key: string | null;
  jira_title: string | null;
  drifted_services: string[];
  drift_events: { id: number; severity: Severity; reasoning: string }[];
}

export interface EngineerGraph {
  engineer_id: string;
  engineer_name: string;
  pull_requests: EngineerPR[];
}
