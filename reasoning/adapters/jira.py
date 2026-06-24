import os
import re
import requests
from models import IntentObject, UnifiedUser

_STATUS_MAP = {
    "To Do": "TODO",
    "In Progress": "IN_PROGRESS",
    "In Review": "READY_FOR_REVIEW",
    "Done": "DONE",
}


def _adf_to_text(node: dict | str | None) -> str:
    """Recursively extracts plain text from Atlassian Document Format (ADF)."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    node_type = node.get("type", "")
    if node_type == "text":
        return node.get("text", "")
    parts = [_adf_to_text(child) for child in node.get("content", [])]
    result = "\n".join(p for p in parts if p)
    # listItem nodes render a bullet in the UI but store no prefix — add one
    if node_type == "listItem":
        return f"- {result}"
    return result


def _parse_acceptance_criteria(text: str) -> list[str]:
    """Extracts bullet-point lines as acceptance criteria."""
    criteria = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and (stripped[0] in ("-", "*", "•") or re.match(r"^\d+\.", stripped)):
            criteria.append(re.sub(r"^[-*•\d.]+\s*", "", stripped).strip())
    return criteria


def _parse_scoped_services(text: str) -> list[str]:
    """Extracts service names matching the pattern *_service from description text."""
    matches = re.findall(r'\b\w+_service\b', text, re.IGNORECASE)
    return list(dict.fromkeys(m.lower() for m in matches))


def fetch_jira_issue(issue_key: str) -> IntentObject:
    """
    Fetches a Jira issue from the Jira Cloud REST API v3 and returns an IntentObject.
    Requires JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in the environment.
    """
    base_url = os.environ["JIRA_BASE_URL"].rstrip("/")
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_API_TOKEN"]
    url = f"{base_url}/rest/api/3/issue/{issue_key}"
    resp = requests.get(url, auth=(email, token), timeout=10)
    resp.raise_for_status()
    return transform_jira_payload(resp.json())


def transform_jira_payload(raw: dict) -> IntentObject:
    """
    Transforms a raw Jira issue payload into an IntentObject.
    Accepts both the Jira webhook format (raw["issue"]) and the direct API response format (raw["key"]).
    """
    issue = raw.get("issue", raw)
    fields = issue["fields"]
    key = issue["key"]

    description = fields.get("description")
    raw_context = _adf_to_text(description) if isinstance(description, dict) else (description or "")

    jira_status = fields.get("status", {}).get("name", "To Do")
    assignee = fields.get("assignee") or {}

    return IntentObject(
        id=f"intent_jira_{key}",
        source_system="jira",
        source_id=key,
        title=fields["summary"],
        raw_context=raw_context,
        acceptance_criteria=_parse_acceptance_criteria(raw_context),
        scoped_services=_parse_scoped_services(raw_context),
        status=_STATUS_MAP.get(jira_status, "TODO"),
        owner=UnifiedUser(
            unified_user_id=f"jira_{assignee.get('accountId', key)}",
            display_name=assignee.get("displayName", "Unassigned"),
            email=assignee.get("emailAddress", ""),
        ),
        last_updated_at=fields.get("updated", ""),
    )
