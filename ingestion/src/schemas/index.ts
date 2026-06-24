export interface UnifiedUser {
  unified_user_id: string;
  display_name: string;
  email: string;
}

export interface IntentObject {
  id: string;
  source_system: 'jira' | 'prd_docs';
  source_id: string;
  title: string;
  raw_context: string;
  acceptance_criteria: string[];
  scoped_services: string[];         // services explicitly in scope (e.g. ["payment_service"])
  status: 'TODO' | 'IN_PROGRESS' | 'READY_FOR_REVIEW' | 'DONE';
  owner: UnifiedUser;
  last_updated_at: string;
}

export interface ExecutionObject {
  id: string;
  source_system: 'github' | 'gitlab';
  source_id: string;
  title: string;
  summary: string;
  author: UnifiedUser;
  push_type: 'pull_request' | 'direct_push';
  target_branch: string;
  status: 'DRAFT' | 'OPEN' | 'MERGED' | 'CLOSED' | 'DIRECT_PUSH';
  changeset: {
    impacted_files: string[];
    diff_summary: string;
  };
  linked_intent_ids: string[];
  last_updated_at: string;
}

export interface DriftAnalysis {
  drift_detected: boolean;
  severity: 'NONE' | 'LOW' | 'HIGH' | 'CRITICAL';
  reasoning: string;
}
