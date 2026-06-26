import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client
from neo4j import GraphDatabase
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from models import AnalyzeRequest, DriftAnalysis, RemediationSpec
from adapters.github import transform_github_payload, fetch_pr_files
from adapters.jira import fetch_jira_issue

load_dotenv()

app = FastAPI(title="Interstellar Reasoning Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
graph_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) if NEO4J_URI and NEO4J_PASSWORD else None

MODEL = os.getenv("REASONING_MODEL", "openai/gpt-oss-120b")
SYSTEM_PROMPT = Path("prompts/drift_detection.txt").read_text()
SPEC_PROMPT = Path("prompts/spec_generation.txt").read_text()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


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
    content = response.choices[0].message.content
    if not content:
        raise HTTPException(status_code=500, detail="LLM returned empty response — retry the request")
    raw = content.strip()
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


def _notify_slack(drift: DriftAnalysis, spec: RemediationSpec, pr_number: int, jira_key: str, repo: str):
    if not SLACK_WEBHOOK_URL:
        print("[slack] SLACK_WEBHOOK_URL not set — skipping")
        return
    try:
        action = spec.action_required.replace("_", " ").title() if spec else "Review required"
        message = (
            f":rotating_light: *Drift detected — PR #{pr_number} ({jira_key})*\n"
            f"*Severity:* {drift.severity}\n"
            f"*Reasoning:* {drift.reasoning}\n"
            f"*Action required:* {action}\n"
            f"*Repo:* https://github.com/{repo}/pull/{pr_number}"
        )
        requests.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=5)
        print(f"[slack] notification sent for PR #{pr_number}")
    except Exception as e:
        print(f"[slack] failed to send notification: {e}")


def _save_to_db(drift: DriftAnalysis, spec, pr_number: int, jira_key: str, repo: str) -> int | None:
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
        return event_id
    except Exception as e:
        print(f"[db] write failed: {e}")
        return None


def _save_to_graph(intent, execution, pr_number: int, jira_key: str, repo: str):
    """Always called — writes base nodes and edges for every PR regardless of drift."""
    if not graph_driver:
        print("[graph] NEO4J_URI not set — skipping")
        return
    try:
        engineer_id = execution.author.unified_user_id
        pr_id = f"pr_{pr_number}"

        with graph_driver.session() as session:
            session.run("""
                MERGE (e:Engineer {id: $engineer_id})
                  SET e.name = $engineer_name
                WITH e
                MERGE (pr:PR {id: $pr_id})
                  SET pr.number = $pr_number, pr.repo = $repo, pr.title = $pr_title
                WITH e, pr
                MERGE (jira:JiraTicket {id: $jira_key})
                  SET jira.title = $jira_title
                WITH e, pr, jira
                MERGE (e)-[:AUTHORED]->(pr)
                MERGE (pr)-[:LINKED_TO]->(jira)
            """, {
                "engineer_id": engineer_id,
                "engineer_name": execution.author.display_name,
                "pr_id": pr_id,
                "pr_number": pr_number,
                "repo": repo,
                "pr_title": execution.title,
                "jira_key": jira_key,
                "jira_title": intent.title,
            })

            for svc in intent.scoped_services:
                session.run("""
                    MERGE (s:Service {id: $svc})
                    WITH s
                    MATCH (jira:JiraTicket {id: $jira_key})
                    MERGE (jira)-[:SCOPED_TO]->(s)
                """, {"svc": svc, "jira_key": jira_key})

        print(f"[graph] base nodes written — PR #{pr_number}, engineer {engineer_id}")
    except Exception as e:
        print(f"[graph] base write failed: {e}")


def _save_drift_to_graph(execution, drift: DriftAnalysis, spec, event_id: int, pr_number: int):
    """Called only when drift detected — layers DriftEvent node and drift edges onto existing PR."""
    if not graph_driver or event_id is None:
        return
    try:
        pr_id = f"pr_{pr_number}"
        drifted_services = [a.service_name for a in spec.affected_services] if spec else []

        with graph_driver.session() as session:
            session.run("""
                MATCH (pr:PR {id: $pr_id})
                CREATE (event:DriftEvent {id: $event_id, severity: $severity, reasoning: $reasoning})
                CREATE (event)-[:PRODUCED]->(pr)
            """, {
                "pr_id": pr_id,
                "event_id": event_id,
                "severity": drift.severity,
                "reasoning": drift.reasoning,
            })

            for svc in drifted_services:
                session.run("""
                    MERGE (s:Service {id: $svc})
                    WITH s
                    MATCH (pr:PR {id: $pr_id})
                    MERGE (pr)-[:DRIFTED_ON]->(s)
                """, {"svc": svc, "pr_id": pr_id})

        print(f"[graph] drift event {event_id} written — PR #{pr_number}")
    except Exception as e:
        print(f"[graph] drift write failed: {e}")


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

    _save_to_graph(intent, execution, pr_number, jira_key, repo)

    spec = None
    if result.drift_detected:
        spec = _run_spec_generation(intent, execution, result, pr_number, jira_key)
        if spec:
            print(f"[ingest/github] spec generated: action_required={spec.action_required}")
        else:
            print(f"[ingest/github] spec generation failed — drift result preserved")
        event_id = _save_to_db(result, spec, pr_number, jira_key, repo)
        _save_drift_to_graph(execution, result, spec, event_id, pr_number)
        _notify_slack(result, spec, pr_number, jira_key, repo)

    return {
        "pr": pr_number,
        "jira_key": jira_key,
        "drift_detected": result.drift_detected,
        "severity": result.severity,
        "reasoning": result.reasoning,
        "remediation_spec": spec.model_dump() if spec else None,
    }


@app.get("/graph/engineer/{engineer_id}")
async def graph_engineer(engineer_id: str):
    if not graph_driver:
        raise HTTPException(status_code=503, detail="Graph database not configured")
    with graph_driver.session() as session:
        records = session.run("""
            MATCH (e:Engineer {id: $id})-[:AUTHORED]->(pr:PR)
            OPTIONAL MATCH (pr)-[:LINKED_TO]->(jira:JiraTicket)
            OPTIONAL MATCH (pr)-[:DRIFTED_ON]->(drifted:Service)
            OPTIONAL MATCH (event:DriftEvent)-[:PRODUCED]->(pr)
            WITH e, pr, jira,
                 collect(DISTINCT drifted.id) AS drifted_services,
                 collect(DISTINCT event {.id, .severity, .reasoning}) AS drift_events
            RETURN
                e.id AS engineer_id,
                e.name AS engineer_name,
                pr.number AS pr_number,
                pr.title AS pr_title,
                pr.repo AS repo,
                jira.id AS jira_key,
                jira.title AS jira_title,
                drifted_services,
                drift_events
        """, {"id": engineer_id})
        rows = [r.data() for r in records]

    if not rows:
        raise HTTPException(status_code=404, detail=f"Engineer '{engineer_id}' not found in graph")

    return {
        "engineer_id": rows[0]["engineer_id"],
        "engineer_name": rows[0]["engineer_name"],
        "pull_requests": [
            {
                "pr_number": r["pr_number"],
                "pr_title": r["pr_title"],
                "repo": r["repo"],
                "jira_key": r["jira_key"],
                "jira_title": r["jira_title"],
                "drifted_services": r["drifted_services"],
                "drift_events": [e for e in r["drift_events"] if e.get("id") is not None],
            }
            for r in rows
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
