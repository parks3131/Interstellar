from pydantic import BaseModel
from typing import Literal

class UnifiedUser(BaseModel):
    unified_user_id: str
    display_name: str
    email: str

class IntentObject(BaseModel):
    id: str
    source_system: Literal['jira', 'prd_docs']
    source_id: str
    title: str
    raw_context: str
    acceptance_criteria: list[str]
    scoped_services: list[str]
    status: Literal['TODO', 'IN_PROGRESS', 'READY_FOR_REVIEW', 'DONE']
    owner: UnifiedUser
    last_updated_at: str

class Changeset(BaseModel):
    impacted_files: list[str]
    diff_summary: str

class ExecutionObject(BaseModel):
    id: str
    source_system: Literal['github', 'gitlab']
    source_id: str
    title: str
    summary: str
    author: UnifiedUser
    push_type: Literal['pull_request', 'direct_push']
    target_branch: str
    status: Literal['DRAFT', 'OPEN', 'MERGED', 'CLOSED', 'DIRECT_PUSH']
    changeset: Changeset
    linked_intent_ids: list[str]
    last_updated_at: str

class AnalyzeRequest(BaseModel):
    intent: IntentObject
    execution: ExecutionObject

class DriftAnalysis(BaseModel):
    drift_detected: bool
    severity: Literal['NONE', 'LOW', 'HIGH', 'CRITICAL']
    reasoning: str

class AffectedService(BaseModel):
    service_name: str
    action: Literal['revert', 'move_to_separate_pr', 'update_intent']
    reason: str

class RemediationSpec(BaseModel):
    pr_number: int
    jira_key: str
    severity: Literal['NONE', 'LOW', 'HIGH', 'CRITICAL']
    summary: str
    affected_services: list[AffectedService]
    suggested_pr_description: str
    owner: str
    action_required: Literal['none', 'revise_pr', 'update_jira', 'escalate']
