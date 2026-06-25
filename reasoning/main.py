import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from models import AnalyzeRequest, DriftAnalysis, RemediationSpec
from adapters.github import transform_github_payload, fetch_pr_files
from adapters.jira import fetch_jira_issue

load_dotenv()

app = FastAPI(title="Interstellar Reasoning Engine")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

MODEL = os.getenv("REASONING_MODEL", "openai/gpt-oss-120b")
SYSTEM_PROMPT = Path("prompts/drift_detection.txt").read_text()
SPEC_PROMPT = Path("prompts/spec_generation.txt").read_text()


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


def _run_spec_generation(intent, execution, drift: DriftAnalysis, pr_number: int, jira_key: str) -> RemediationSpec | None:
    user_message = f"""
IntentObject:
{intent.model_dump_json(indent=2)}

ExecutionObject:
{execution.model_dump_json(indent=2)}

DriftAnalysis:
{drift.model_dump_json(indent=2)}
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SPEC_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        raw = response.choices[0].message.content.strip()
        llm_output = json.loads(raw)
        return RemediationSpec(
            pr_number=pr_number,
            jira_key=jira_key,
            severity=drift.severity,
            owner=execution.author.display_name,
            **llm_output,
        )
    except Exception as e:
        print(f"[spec_generation] Failed: {e}")
        return None


def _save_to_db(drift: DriftAnalysis, spec, pr_number: int, jira_key: str, repo: str):
    try:
        row = db.table("drift_events").insert({
            "pr_number": pr_number,
            "jira_key": jira_key,
            "severity": drift.severity,
            "reasoning": drift.reasoning,
            "repo": repo,
        }).execute()

        event_id = row.data[0]["id"]

        if spec:
            db.table("remediation_specs").insert({
                "drift_event_id": event_id,
                "spec": spec.model_dump(),
                "status": "open",
            }).execute()

        print(f"[db] saved drift_event id={event_id}")
    except Exception as e:
        print(f"[db] write failed: {e}")


class AcknowledgeRequest(BaseModel):
    drift_event_id: int
    note: str | None = None


@app.get("/drift-history")
async def drift_history():
    events = db.table("drift_events").select("*, remediation_specs(*)").order("created_at", desc=True).execute()
    return events.data


@app.post("/acknowledge")
async def acknowledge(body: AcknowledgeRequest):
    event = db.table("drift_events").select("id").eq("id", body.drift_event_id).execute()
    if not event.data:
        raise HTTPException(status_code=404, detail=f"drift_event {body.drift_event_id} not found")

    db.table("acknowledged_flags").insert({
        "drift_event_id": body.drift_event_id,
        "note": body.note,
    }).execute()

    db.table("remediation_specs").update({"status": "acknowledged"}).eq("drift_event_id", body.drift_event_id).execute()

    return {"acknowledged": True, "drift_event_id": body.drift_event_id}


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

    spec = None
    if result.drift_detected:
        spec = _run_spec_generation(intent, execution, result, pr_number, jira_key)
        if spec:
            print(f"[ingest/github] spec generated: action_required={spec.action_required}")
        else:
            print(f"[ingest/github] spec generation failed — drift result preserved")
        _save_to_db(result, spec, pr_number, jira_key, repo)

    return {
        "pr": pr_number,
        "jira_key": jira_key,
        "drift_detected": result.drift_detected,
        "severity": result.severity,
        "reasoning": result.reasoning,
        "remediation_spec": spec.model_dump() if spec else None,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
