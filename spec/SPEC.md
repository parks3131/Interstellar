# Interstellar — Living Spec

This file is the single source of truth for what has been built, how each part works, and what comes next.
Update this file at the end of every phase.

---

## What Interstellar Is

A developer intelligence platform that connects your tools (Jira, Slack, GitHub, Figma, Docs) and reasons across them to detect when what's being built has drifted from what was intended — then generates structured specs for AI agents to act on.

**Core flow:**
```
Ingest → Reason → [Flag or Spec] → Agent executes
```

---

## Stack Decision

The entire backend is Python / FastAPI.

- One language, one runtime, one set of dependencies
- Pydantic handles all schema validation (request bodies, response shapes)
- FastAPI handles all HTTP routing (webhooks in Phase 3, reasoning in Phase 1)
- The TypeScript ingestion layer was removed after Phase 1

---

## Project Structure

```
Interstellar/
├── reasoning/              # The entire backend
│   ├── main.py             # FastAPI server — all routes live here
│   ├── models.py           # All Pydantic schemas (IntentObject, ExecutionObject, etc.)
│   ├── prompts/
│   │   └── drift_detection.txt  # System prompt for the LLM
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── github.py       # transform_github_payload + fetch_pr_files
│   │   └── jira.py         # transform_jira_payload + fetch_jira_issue
│   ├── scripts/
│   │   ├── test_scenarios.py    # Phase 1 — posts mock objects to /analyze (server must be running)
│   │   └── test_adapters.py     # Phase 2 — runs adapters on raw mock data (no server needed)
│   ├── requirements.txt
│   ├── .env                # Secret keys — never committed
│   └── .env.example        # Template showing what keys are needed
├── shared/
│   └── mock/               # Static test scenarios (no real APIs needed)
│       ├── scenario1_aligned.json
│       ├── scenario2_scope_creep.json
│       ├── scenario3_policy_violation.json
│       ├── raw_github_pr.json    # Raw GitHub PR webhook payload (for adapter tests)
│       └── raw_jira_issue.json   # Raw Jira API response with ADF description
├── spec/
│   └── SPEC.md             # This file
└── README.md
```

---

## Schemas (the shared language)

All schemas defined in `reasoning/models.py` using Pydantic.

### UnifiedUser
Represents a person across any tool.

| Field | What it holds |
|---|---|
| `unified_user_id` | Internal ID e.g. `user_001` |
| `display_name` | Full name |
| `email` | Email address |

### IntentObject
Represents what was **planned**. Sourced from Jira or a PRD.

| Field | What it holds |
|---|---|
| `id` | Internal ID e.g. `intent_jira_INT-402` |
| `source_system` | `jira` or `prd_docs` |
| `source_id` | The actual Jira key e.g. `INT-402` |
| `title` | Ticket title |
| `raw_context` | Full ticket description |
| `acceptance_criteria` | Parsed bullet points from the ticket |
| `scoped_services` | Services explicitly in scope e.g. `["payment_service"]` |
| `status` | TODO / IN_PROGRESS / READY_FOR_REVIEW / DONE |
| `owner` | UnifiedUser |
| `last_updated_at` | ISO timestamp |

### ExecutionObject
Represents what was **built**. Sourced from a GitHub PR or direct push.

| Field | What it holds |
|---|---|
| `id` | Internal ID e.g. `exec_gh_pr_84` |
| `source_system` | `github` or `gitlab` |
| `source_id` | PR number or commit SHA |
| `title` | PR title |
| `summary` | PR description body |
| `author` | UnifiedUser |
| `push_type` | `pull_request` or `direct_push` |
| `target_branch` | Which branch was targeted — key for detecting main pushes |
| `status` | DRAFT / OPEN / MERGED / CLOSED / DIRECT_PUSH |
| `changeset.impacted_files` | Every file path touched |
| `changeset.diff_summary` | Human-readable summary of what changed |
| `linked_intent_ids` | Jira keys found in PR title/body e.g. `["INT-402"]` |
| `last_updated_at` | ISO timestamp |

### DriftAnalysis
The output of the reasoning engine.

| Field | What it holds |
|---|---|
| `drift_detected` | true / false |
| `severity` | NONE / LOW / HIGH / CRITICAL |
| `reasoning` | One specific sentence explaining the judgment |

---

## Phase 1 — Mock Data & Reasoning Test ✅

**Goal:** Prove the AI reasoning layer can detect drift before connecting any real APIs.

**What was built:**

| File | Role |
|---|---|
| `reasoning/models.py` | All Pydantic schemas |
| `reasoning/prompts/drift_detection.txt` | System prompt — instructs the LLM to compare intent vs execution and return structured JSON |
| `reasoning/main.py` | FastAPI server — POST /analyze receives intent + execution, calls OpenRouter LLM, returns DriftAnalysis |
| `shared/mock/scenario1_aligned.json` | Coupon code PR touching only payment_service — expects NONE |
| `shared/mock/scenario2_scope_creep.json` | Same ticket but PR also touches user_auth_service — expects HIGH |
| `shared/mock/scenario3_policy_violation.json` | Critical bug fix pushed directly to main with no PR — expects CRITICAL |
| `reasoning/scripts/test_scenarios.py` | Loads all 3 mock files, posts them to /analyze, prints results |

**How to run:**
```bash
# Terminal 1 — start reasoning server
cd reasoning && .venv/bin/uvicorn main:app --reload

# Terminal 2 — run the test
cd reasoning && .venv/bin/python scripts/test_scenarios.py
```

**Results confirmed:**
- Scenario 1: `drift_detected: false` / `NONE` — passed correctly
- Scenario 2: `drift_detected: true` / `HIGH` — caught scope creep into user_auth_service
- Scenario 3: `drift_detected: true` / `CRITICAL` — caught direct push bypassing PR requirement

**Model:** `openai/gpt-oss-120b` via OpenRouter
**Config:** `reasoning/.env` (never committed — in .gitignore)

---

## Phase 2 — Ingest Adapters ✅

**Goal:** Build the transformation layer that accepts real GitHub and Jira webhook payloads and maps them into IntentObject / ExecutionObject.

**What was built:**

| File | Role |
|---|---|
| `reasoning/adapters/__init__.py` | Makes `adapters/` a Python package |
| `reasoning/adapters/github.py` | `transform_github_payload(raw, files?)` → ExecutionObject |
| `reasoning/adapters/jira.py` | `transform_jira_payload(raw)` → IntentObject, `fetch_jira_issue(key)` → IntentObject |
| `shared/mock/raw_github_pr.json` | Realistic GitHub PR webhook payload with injected `_files` array |
| `shared/mock/raw_jira_issue.json` | Realistic Jira API response with ADF description |
| `reasoning/scripts/test_adapters.py` | Runs both adapters against mock data — no server or credentials required |
| `reasoning/.env.example` | Updated with GITHUB_TOKEN, JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN |

**Key decisions:**

- **Real-time fetch** — when a GitHub webhook arrives (Phase 3), extract the Jira key from PR title, call `fetch_jira_issue(key)` immediately. No DB needed.
- **ADF handling** — Jira Cloud returns description in Atlassian Document Format (JSON). `_adf_to_text()` recursively extracts plain text, adding `- ` prefix to `listItem` nodes so bullet points survive.
- **Jira key regex** — `\b[A-Z]+-\d+\b` on PR title + body. Word-boundary anchors prevent false matches inside longer tokens. Order-preserving deduplication via `dict.fromkeys`.
- **`files` parameter** — pass explicitly in tests to skip the GitHub API call; `None` triggers `fetch_pr_files()` in production.

**How to run (no server, no credentials):**
```bash
cd reasoning && .venv/bin/python scripts/test_adapters.py
```

**Results confirmed:**

GitHub adapter:
- `id`: `exec_gh_pr_85`
- `linked_intent_ids`: `['INT-402']` — extracted from PR title
- `impacted_files`: 3 files including `user_auth_service/session.py` (the scope creep file)
- `status`: OPEN

Jira adapter:
- `id`: `intent_jira_INT-402`
- `scoped_services`: `['payment_service']` — parsed from description text
- `acceptance_criteria`: 4 bullet points correctly extracted from ADF
- `status`: IN_PROGRESS

**New env vars required** (add to `reasoning/.env`):
```
GITHUB_TOKEN=...          # read-only repo scope
JIRA_BASE_URL=...         # https://yourorg.atlassian.net
JIRA_EMAIL=...
JIRA_API_TOKEN=...        # from id.atlassian.com
```

---

## Phase 3 — Live Webhook Gateway ✅

**Goal:** Expose real endpoints, receive live GitHub webhooks, fetch Jira in real-time, and fire reasoning automatically.

**What was built:**

| File | Change |
|---|---|
| `reasoning/main.py` | Added `POST /ingest/github` route |

**How `/ingest/github` works:**
1. Receives raw GitHub PR webhook (action: opened / reopened / synchronize / edited)
2. Extracts Jira key from PR title + body using regex
3. Calls `fetch_jira_issue(key)` → live Jira API call → IntentObject
4. Calls `fetch_pr_files(repo, pr_number)` → live GitHub API call → file list
5. Transforms both → runs `_run_reasoning()` → DriftAnalysis
6. Returns JSON with `pr`, `jira_key`, `drift_detected`, `severity`, `reasoning`

**Infrastructure:**
- ngrok exposes `localhost:8000` as a public HTTPS URL
- GitHub webhook registered on `parks3131/Interstellar` → fires on Pull request events
- No DB — Jira ticket is fetched live when the webhook arrives

**How to run:**
```bash
# Terminal 1 — server
cd reasoning && .venv/bin/uvicorn main:app --reload

# Terminal 2 — tunnel
ngrok http 8000
```

**Live test result — PR #6 (SCRUM-5):**
```
[ingest/github] PR #6 — linked to SCRUM-5
[ingest/github] Fetched SCRUM-5: 'Add coupon code support at checkout.'
[ingest/github] PR files: ['ingestion/...', 'reasoning/adapters/coupon.py', ...]
[ingest/github] drift=True  severity=HIGH
[ingest/github] reasoning: The PR changes files in ingestion and reasoning components
                            rather than the payment_service specified in the intent,
                            violating the scoped service constraint.
```

The Jira ticket scoped work to `payment_service` only. The real PR touched `reasoning/` and `ingestion/`. The LLM correctly flagged HIGH drift on live data.

---

## Phase 4 — Spec Generation (next)

**Goal:** When drift is detected, don't just log it — generate a structured remediation spec that tells someone exactly what to do to realign the PR with the intent. This completes the core loop: detect → specify → act.

**What to build:**

| File | What it does |
|---|---|
| `reasoning/models.py` | Add `RemediationSpec` Pydantic model |
| `reasoning/prompts/spec_generation.txt` | New system prompt for spec generation |
| `reasoning/main.py` | Call spec generation after drift detected in `/ingest/github` |

**`RemediationSpec` schema (to add to `models.py`):**
```python
class AffectedService(BaseModel):
    service_name: str
    action: Literal['revert', 'move_to_separate_pr', 'update_intent']
    reason: str

class RemediationSpec(BaseModel):
    pr_number: int
    jira_key: str
    severity: Literal['NONE', 'LOW', 'HIGH', 'CRITICAL']
    summary: str                    # one sentence: what drifted and why it matters
    affected_services: list[AffectedService]
    suggested_pr_description: str   # rewritten PR body that would be aligned
    owner: str                      # display name of the PR author
    action_required: Literal['none', 'revise_pr', 'update_jira', 'escalate']
```

**New system prompt (`reasoning/prompts/spec_generation.txt`):**
```
You are Interstellar's spec generator. Given a DriftAnalysis and the IntentObject + ExecutionObject that produced it, generate a RemediationSpec.
Return JSON only. No markdown.
Schema: { "summary": str, "affected_services": [{"service_name": str, "action": "revert"|"move_to_separate_pr"|"update_intent", "reason": str}], "suggested_pr_description": str, "action_required": "none"|"revise_pr"|"update_jira"|"escalate" }
```

**Flow change in `/ingest/github`:**
```
drift detected → call spec generation LLM → return RemediationSpec alongside DriftAnalysis
```

**Expected output for SCRUM-5 / PR #6:**
```json
{
  "pr_number": 6,
  "jira_key": "SCRUM-5",
  "severity": "HIGH",
  "summary": "PR modifies user_auth_service and ingestion layer but SCRUM-5 scopes work to payment_service only.",
  "affected_services": [
    {"service_name": "user_auth_service", "action": "move_to_separate_pr", "reason": "Not in scope for SCRUM-5"},
    {"service_name": "ingestion", "action": "move_to_separate_pr", "reason": "Not in scope for SCRUM-5"}
  ],
  "suggested_pr_description": "Implements coupon code logic in payment_service only. Adds coupon validation endpoint and discount calculation. No other services touched.",
  "action_required": "revise_pr"
}
```

---

## Phase 5 — Database (after Phase 4)

**Goal:** Persist every drift event and generated spec so they can be reviewed, acknowledged, and surfaced in a dashboard.

**What to build:**
- PostgreSQL via Supabase (free tier, no infra to manage)
- Tables: `drift_events`, `remediation_specs`, `acknowledged_flags`
- `drift_events`: pr_number, jira_key, severity, reasoning, timestamp, repo
- `remediation_specs`: links to drift_event, full spec JSON, status (open / acknowledged / resolved)
- New endpoint: `GET /drift-history` — returns all past events
- New endpoint: `POST /acknowledge` — marks a drift event as seen/handled

**Why Supabase:** Gives you a Postgres DB + REST API + dashboard with zero server setup. Free tier is enough for this project.

---

## Phase 6 — Slack Notification (after Phase 5)

**Goal:** When drift is detected and a spec is generated, post a Slack message to the right channel so the right person is interrupted in real time.

**What to build:**
- Slack incoming webhook (no bot needed, just a webhook URL)
- After spec generation in `/ingest/github`, post a formatted message:
  ```
  🚨 Drift detected — PR #6 (SCRUM-5)
  Severity: HIGH
  SCRUM-5 scopes to payment_service only. PR also touches user_auth_service and ingestion.
  Action required: Revise PR
  → github.com/parks3131/Interstellar/pull/6
  ```
- New env var: `SLACK_WEBHOOK_URL`

**Why this matters:** Right now drift prints to a terminal only you can see. Slack makes it visible to the whole team the moment it happens.

---

## Credentials Reference

All secrets live in `reasoning/.env` — never committed. Template in `reasoning/.env.example`.

| Key | Where to generate | Used by |
|---|---|---|
| `OPENROUTER_API_KEY` | openrouter.ai/keys | LLM calls (drift detection, spec generation) |
| `REASONING_MODEL` | — | Set to `openai/gpt-oss-120b` |
| `GITHUB_TOKEN` | github.com/settings/tokens | Fetch PR files |
| `JIRA_BASE_URL` | — | `https://rpkparks.atlassian.net` |
| `JIRA_EMAIL` | — | `rpkparks@gmail.com` |
| `JIRA_API_TOKEN` | id.atlassian.com/manage-profile/security/api-tokens | Fetch Jira tickets |
| `SLACK_WEBHOOK_URL` | Phase 6 — api.slack.com/apps | Post drift alerts |

**Rotate all tokens after sharing in chat.** Generate new ones and update `.env` directly.

---

## How to Start a Session

```bash
# Kill anything on 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Start server
cd ~/Developer/Interstellar/reasoning && .venv/bin/uvicorn main:app --reload

# Start tunnel (second terminal)
ngrok http 8000
```

Update the GitHub webhook URL at `github.com/parks3131/Interstellar/settings/hooks` if ngrok gave you a new URL (ngrok free tier gives a new URL every restart).
