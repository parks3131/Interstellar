import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, HTTPException, Request
from models import AnalyzeRequest, DriftAnalysis
from adapters.github import transform_github_payload, fetch_pr_files
from adapters.jira import fetch_jira_issue

load_dotenv()

app = FastAPI(title="Interstellar Reasoning Engine")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = os.getenv("REASONING_MODEL", "openai/gpt-oss-120b")
SYSTEM_PROMPT = Path("prompts/drift_detection.txt").read_text()


def _run_reasoning(intent, execution) -> DriftAnalysis:
    user_message = f"""
IntentObject:
{intent.model_dump_json(indent=2)}

ExecutionObject:
{execution.model_dump_json(indent=2)}
"""
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    raw = response.choices[0].message.content.strip()
    try:
        return DriftAnalysis(**json.loads(raw))
    except Exception:
        raise HTTPException(status_code=500, detail=f"Failed to parse reasoning output: {raw}")


@app.post("/analyze", response_model=DriftAnalysis)
async def analyze(request: AnalyzeRequest) -> DriftAnalysis:
    return _run_reasoning(request.intent, request.execution)


@app.post("/ingest/github")
async def ingest_github(request: Request):
    raw = await request.json()

    # Only process PR open/reopen/sync events — ignore everything else
    action = raw.get("action")
    if action not in ("opened", "reopened", "synchronize", "edited"):
        return {"skipped": True, "reason": f"action '{action}' ignored"}

    if "pull_request" not in raw:
        return {"skipped": True, "reason": "not a pull_request event"}

    pr = raw["pull_request"]
    pr_number = pr["number"]
    repo = raw["repository"]["full_name"]
    title = pr["title"]

    # Extract Jira key from PR title
    from adapters.github import _extract_jira_keys
    jira_keys = _extract_jira_keys(title + " " + (pr.get("body") or ""))

    if not jira_keys:
        print(f"[ingest/github] PR #{pr_number} — no Jira key found in title/body, skipping reasoning")
        return {"skipped": True, "reason": "no Jira key found in PR title or body"}

    jira_key = jira_keys[0]
    print(f"[ingest/github] PR #{pr_number} — linked to {jira_key}")

    # Real-time fetch: get Jira ticket now
    try:
        intent = fetch_jira_issue(jira_key)
        print(f"[ingest/github] Fetched {jira_key}: '{intent.title}'")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Jira issue {jira_key}: {e}")

    # Fetch changed files from GitHub API
    try:
        files = fetch_pr_files(repo, pr_number)
        print(f"[ingest/github] PR files: {files}")
    except Exception as e:
        print(f"[ingest/github] Warning: could not fetch PR files: {e}")
        files = []

    execution = transform_github_payload(raw, files=files)

    # Run reasoning
    result = _run_reasoning(intent, execution)

    print(f"[ingest/github] drift={result.drift_detected} severity={result.severity}")
    print(f"[ingest/github] reasoning: {result.reasoning}")

    return {
        "pr": pr_number,
        "jira_key": jira_key,
        "drift_detected": result.drift_detected,
        "severity": result.severity,
        "reasoning": result.reasoning,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
