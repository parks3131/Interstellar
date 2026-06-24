import os
import re
import requests
from models import ExecutionObject, UnifiedUser, Changeset

JIRA_KEY_PATTERN = re.compile(r'\b[A-Z]+-\d+\b')

_STATUS_MAP = {
    ("open", False, False): "OPEN",
    ("open", True, False): "DRAFT",
    ("closed", False, True): "MERGED",
    ("closed", False, False): "CLOSED",
}


def _extract_jira_keys(text: str) -> list[str]:
    return list(dict.fromkeys(JIRA_KEY_PATTERN.findall(text or "")))


def _map_status(state: str, draft: bool, merged: bool) -> str:
    return _STATUS_MAP.get((state, draft, merged), "OPEN")


def fetch_pr_files(repo: str, pr_number: int) -> list[str]:
    """Calls GitHub REST API to get all files changed in a PR."""
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return [f["filename"] for f in resp.json()]


def transform_github_payload(raw: dict, files: list[str] | None = None) -> ExecutionObject:
    """
    Transforms a raw GitHub PR webhook payload into an ExecutionObject.

    Pass `files` explicitly to skip the GitHub API call (useful in tests).
    If `files` is None, calls fetch_pr_files() using GITHUB_TOKEN from env.
    """
    pr = raw["pull_request"]
    repo = raw["repository"]["full_name"]
    pr_number = pr["number"]

    title = pr["title"]
    body = pr.get("body") or ""
    state = pr["state"]
    draft = pr.get("draft", False)
    merged = pr.get("merged", False)

    author_login = pr["user"]["login"]
    author_email = pr["user"].get("email") or f"{author_login}@users.noreply.github.com"

    if files is None:
        try:
            files = fetch_pr_files(repo, pr_number)
        except Exception:
            files = []

    jira_keys = _extract_jira_keys(title + " " + body)
    file_count = len(files)

    return ExecutionObject(
        id=f"exec_gh_pr_{pr_number}",
        source_system="github",
        source_id=str(pr_number),
        title=title,
        summary=body,
        author=UnifiedUser(
            unified_user_id=f"gh_{author_login}",
            display_name=author_login,
            email=author_email,
        ),
        push_type="pull_request",
        target_branch=pr["base"]["ref"],
        status=_map_status(state, draft, merged),
        changeset=Changeset(
            impacted_files=files,
            diff_summary=f"PR #{pr_number} modifies {file_count} file(s): {', '.join(files[:3])}{'...' if file_count > 3 else ''}",
        ),
        linked_intent_ids=jira_keys,
        last_updated_at=pr["updated_at"],
    )
