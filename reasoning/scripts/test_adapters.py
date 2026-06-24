"""
Phase 2 adapter test — no server required, no credentials required.

Loads raw mock payloads and runs them through the GitHub and Jira transform
functions directly, then prints the resulting IntentObject and ExecutionObject.
"""
import sys
import json
from pathlib import Path

# Allow importing from reasoning/ when run from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.github import transform_github_payload
from adapters.jira import transform_jira_payload

MOCK_DIR = Path(__file__).parent.parent.parent / "shared" / "mock"


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


def run() -> None:
    github_raw = json.loads((MOCK_DIR / "raw_github_pr.json").read_text())
    jira_raw = json.loads((MOCK_DIR / "raw_jira_issue.json").read_text())

    section(f"GitHub adapter — {github_raw['_label']}")
    execution = transform_github_payload(github_raw, files=github_raw["_files"])
    print(f"id              : {execution.id}")
    print(f"title           : {execution.title}")
    print(f"author          : {execution.author.display_name} ({execution.author.email})")
    print(f"target_branch   : {execution.target_branch}")
    print(f"status          : {execution.status}")
    print(f"linked_intents  : {execution.linked_intent_ids}")
    print(f"impacted_files  : {execution.changeset.impacted_files}")
    print(f"diff_summary    : {execution.changeset.diff_summary}")

    section(f"Jira adapter — {jira_raw['_label']}")
    intent = transform_jira_payload(jira_raw)
    print(f"id              : {intent.id}")
    print(f"title           : {intent.title}")
    print(f"status          : {intent.status}")
    print(f"owner           : {intent.owner.display_name} ({intent.owner.email})")
    print(f"scoped_services : {intent.scoped_services}")
    print(f"acceptance_crit : {intent.acceptance_criteria}")
    print(f"raw_context     :\n{intent.raw_context[:200]}...")


if __name__ == "__main__":
    run()
