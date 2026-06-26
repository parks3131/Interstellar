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
├── dashboard/              # Next.js 16 frontend (Phase 8)
│   ├── app/
│   │   ├── page.tsx                    # Drift feed — server component
│   │   ├── layout.tsx                  # Root layout with Geist font
│   │   ├── globals.css                 # Tailwind v4 + dark theme
│   │   ├── lib/
│   │   │   └── types.ts                # TypeScript types matching API shapes
│   │   ├── components/
│   │   │   ├── DriftCard.tsx           # Per-event card with spec, services, owner link
│   │   │   ├── ServiceHeatmap.tsx      # Bar chart computed from affected_services
│   │   │   └── AcknowledgeButton.tsx   # Client component — POSTs to /acknowledge
│   │   └── engineer/[id]/
│   │       └── page.tsx                # Engineer view — pulls from /graph/engineer/{id}
│   ├── .env.local                      # NEXT_PUBLIC_API_URL=http://localhost:8000
│   └── package.json
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

## Phase 4 — Spec Generation ✅

**Goal:** When drift is detected, don't just log it — generate a structured remediation spec that tells someone exactly what to do to realign the PR with the intent. This completes the core loop: detect → specify → act.

**What was built:**

| File | What it does |
|---|---|
| `reasoning/models.py` | Added `AffectedService` and `RemediationSpec` Pydantic models |
| `reasoning/prompts/spec_generation.txt` | System prompt — LLM returns only 4 judgment fields; code fills the rest |
| `reasoning/main.py` | `_run_spec_generation()` — second LLM call after drift detected; degrades gracefully on failure |
| `reasoning/scripts/test_spec_generation.py` | Standalone test — runs drift + spec against scenario2 mock, no server needed |

**Key decisions:**
- LLM returns only judgment fields: `summary`, `affected_services`, `suggested_pr_description`, `action_required`
- Code fills known fields: `pr_number`, `jira_key`, `severity`, `owner` — never ask the LLM for data you already have
- Spec generation failure returns `remediation_spec: null` — drift result is never lost

**How to test (no server, no credentials except OPENROUTER_API_KEY):**
```bash
cd reasoning && .venv/bin/python scripts/test_spec_generation.py
```

**Live test result — PR #10 (SCRUM-5):**
```json
{
  "pr_number": 10,
  "jira_key": "SCRUM-5",
  "severity": "HIGH",
  "summary": "The PR modifies reasoning/out_of_scope_change.py, which is outside the payment_service scope required for SCRUM-5.",
  "affected_services": [
    {"service_name": "reasoning", "action": "revert", "reason": "Changes to reasoning/out_of_scope_change.py are unrelated to coupon code support and violate the intent that only payment_service be touched."}
  ],
  "suggested_pr_description": "Implements coupon code support at checkout as defined in SCRUM-5...",
  "owner": "parks3131",
  "action_required": "revise_pr"
}
```

---

## Phase 5 — Database ✅

**Goal:** Persist every drift event and generated spec so they can be reviewed, acknowledged, and surfaced in a dashboard.

**What was built:**

| File | Change |
|---|---|
| `reasoning/main.py` | Supabase client, `_save_to_db()`, `GET /drift-history`, `POST /acknowledge` |
| `reasoning/requirements.txt` | Added `supabase==2.31.0` |

**Database:** PostgreSQL via Supabase (project: `interstellar`, region: `us-east-1`)

**Tables:**
```sql
drift_events        — pr_number, jira_key, severity, reasoning, repo, created_at
remediation_specs   — drift_event_id (FK), spec (jsonb), status, created_at
acknowledged_flags  — drift_event_id (FK), note, acknowledged_at
```

**Spec status lifecycle:**
```
open → acknowledged → resolved
```
- `open` — drift detected, nobody has acted yet
- `acknowledged` — team marked it via `POST /acknowledge`
- `resolved` — PR revised or Jira updated (future phase)

**New endpoints:**
- `GET /drift-history` — returns all drift events with nested remediation specs
- `POST /acknowledge` — body: `{"drift_event_id": int, "note": str | null}`

**DB write degrades gracefully** — if Supabase is unreachable, drift + spec still return in the response; only persistence fails.

**New env vars required:**
```
SUPABASE_URL=https://kjdlggncnwcsfbxypexi.supabase.co
SUPABASE_KEY=your_secret_key
```

**Live test result — PR #10:**
```
[db] saved drift_event id=1
GET /drift-history → returns event with nested remediation_spec, status: open
```

---

## Phase 6 — Slack Notification ✅

**Goal:** When drift is detected and a spec is generated, post a Slack message to the right channel so the right person is interrupted in real time.

**What was built:**

| File | Change |
|---|---|
| `reasoning/main.py` | `_notify_slack()` — fires after `_save_to_db()` when drift detected |

**How it works:**
- Uses a Slack incoming webhook — no bot, no OAuth, just a POST to a URL
- Called after spec generation and DB write in `/ingest/github`
- Degrades gracefully — if `SLACK_WEBHOOK_URL` is not set or the call fails, the rest of the flow is unaffected

**Message format:**
```
🚨 Drift detected — PR #13 (SCRUM-5)
Severity: HIGH
Reasoning: The PR only modifies an unrelated test file and does not implement any payment_service changes.
Action required: Revise Pr
Repo: https://github.com/parks3131/Interstellar/pull/13
```

**Slack setup:**
- Workspace: `Interstellar`
- Channel: `#drift-alerts`
- App: `Interstellar` (incoming webhook)

**New env var:**
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

**Live test result — PR #13 (SCRUM-5):**
Slack message appeared in `#drift-alerts` instantly when the PR was opened. Severity HIGH, correct reasoning, clickable repo link.

---

## Phase 7 — Graph Layer ✅

**Goal:** Connect entities across tools into a knowledge graph so Interstellar can answer relationship questions — not just log events.

**Why this matters:** Postgres stores what happened. The graph stores how things connect. Once you have enough drift events across PRs, engineers, services, and tickets, you need to traverse relationships — not scan rows.

**Questions the graph enables:**
- Which engineers consistently drift on the same service?
- Which Jira tickets share the same service scope and are likely to conflict?
- Show me everything connected to this incident

**What was built:**

| File | Change |
|---|---|
| `reasoning/main.py` | `GraphDatabase.driver` init (degrades if env vars absent), `_save_to_graph()`, `_save_drift_to_graph()`, `GET /graph/engineer/{id}` |
| `reasoning/requirements.txt` | Added `neo4j==5.22.0` |
| `reasoning/.env.example` | Added `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` |

**Graph write is split into two functions:**

`_save_to_graph()` — called on **every PR** regardless of drift:
- Writes `Engineer`, `PR`, `JiraTicket`, `Service` nodes
- Writes `AUTHORED`, `LINKED_TO`, `SCOPED_TO` edges

`_save_drift_to_graph()` — called **only when drift detected**, layered on top:
- Creates `DriftEvent` node
- Writes `PRODUCED`, `DRIFTED_ON` edges

This split means aligned PRs are still in the graph — enabling ratio tracking, service ownership mapping, and conflict prediction — while drift signals are layered on top.

**Nodes (all MERGE except DriftEvent which is CREATE):**
- `Engineer {id, name}`
- `PR {id, number, repo, title}`
- `JiraTicket {id, title}`
- `Service {id}`
- `DriftEvent {id, severity, reasoning}`

**Edges:**
- `(Engineer)-[:AUTHORED]->(PR)`
- `(PR)-[:LINKED_TO]->(JiraTicket)`
- `(JiraTicket)-[:SCOPED_TO]->(Service)` — from `intent.scoped_services`
- `(PR)-[:DRIFTED_ON]->(Service)` — from `spec.affected_services`
- `(DriftEvent)-[:PRODUCED]->(PR)`

**New endpoint:**
- `GET /graph/engineer/{engineer_id}` — returns engineer + all PRs with linked Jira keys, drifted services, and drift events

**Storage split:**
```
Postgres (Supabase)     →  event log — what happened, when
Neo4j (Aura)            →  knowledge graph — how entities connect
```

**New env vars required:**
```
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io   # from console.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_generated_password
```

**Live test results:**
- PR #20 (SCRUM-8, aligned) — `[graph] base nodes written`, no DriftEvent node
- PR #18 (SCRUM-5, drifted) — `[graph] base nodes written` + `[graph] drift event written`
- Neo4j graph shows parks3131 at center with all PRs radiating out; drifted PRs have pink DriftEvent nodes, aligned PRs do not

**Setup:** Create a free Aura instance at console.neo4j.io — provisions in ~2 minutes. Download credentials immediately (shown only once).

---

## Phase 8 — Dashboard ✅

**Goal:** Surface drift history, trends, and ownership in a visual UI so the team doesn't have to curl endpoints to see what's happening.

**What was built:**

| File | Role |
|---|---|
| `dashboard/app/page.tsx` | Drift feed — server component, fetches `/drift-history`, renders all events newest-first |
| `dashboard/app/components/DriftCard.tsx` | Per-event card: severity badge, reasoning, remediation summary, service tags, owner link, acknowledge button |
| `dashboard/app/components/ServiceHeatmap.tsx` | Bar chart: counts `affected_services` across all events, colour-coded by frequency |
| `dashboard/app/components/AcknowledgeButton.tsx` | Client component — POSTs to `/acknowledge`, flips to "✓ Acknowledged" instantly |
| `dashboard/app/engineer/[id]/page.tsx` | Engineer view — calls `/graph/engineer/{id}`, shows all PRs with Aligned / drift badges, Jira keys, and per-event reasoning |
| `dashboard/app/lib/types.ts` | TypeScript types matching exact shapes returned by `/drift-history` and `/graph/engineer/{id}` |
| `reasoning/main.py` | Added `CORSMiddleware` for `http://localhost:3000` so the dashboard can call the FastAPI backend |

**Stack:** Next.js 16 + Tailwind v4 + TypeScript, dark theme

**Key decisions:**
- Pages are server components — data is fetched at request time (`cache: "no-store"`) directly from FastAPI
- `AcknowledgeButton` is the only client component — needed for the click handler
- Service heatmap is computed entirely from `/drift-history` data on the client — no extra endpoint needed
- Engineer IDs in Neo4j use the `gh_{username}` format (set by the GitHub adapter's `unified_user_id`). Links from `DriftCard` use `/engineer/gh_${owner}` accordingly
- `params` in dynamic routes is a `Promise<{ id: string }>` in Next.js 16 — must be awaited

**How to run:**
```bash
cd dashboard && npm run dev
# → http://localhost:3000
```

Requires FastAPI running on `localhost:8000` (see session startup instructions below).

**Live test results:**
- Drift feed loaded all 8 events with correct severity badges, reasoning, and specs
- Service heatmap showed `reasoning` (5 hits, red) and `test_graph` (1, yellow)
- Engineer view at `/engineer/gh_parks3131` showed 5 PRs, 4 drifts, PR #20 correctly showing "Aligned"
- Acknowledge button on PR #19 flipped to "✓ Acknowledged" and updated Supabase in real time

---

## Phase 9 — Agent Execution (after Phase 8)

**Goal:** Close the loop fully. Instead of telling a human to revise the PR, hand the remediation spec to an AI agent and let it act.

**What to build:**
- Agent receives a `RemediationSpec` with `action_required: revise_pr`
- Agent opens the PR, reads the diff, removes out-of-scope changes, updates the PR description
- Agent posts a comment on the PR: "Scope corrected per SCRUM-5 — removed changes to user_auth_service"
- Human reviews and merges

**Full loop:**
```
GitHub PR opened
→ Interstellar detects drift
→ Spec generated
→ Agent revises PR automatically
→ Human reviews revised PR
→ Merge
```

**This is the end state:** Interstellar doesn't just flag drift — it fixes it.

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
| `SUPABASE_URL` | supabase.com project settings | Supabase DB client |
| `SUPABASE_KEY` | supabase.com project settings → API Keys → Secret | Supabase DB client |
| `SLACK_WEBHOOK_URL` | Phase 6 — api.slack.com/apps | Post drift alerts |
| `NEO4J_URI` | console.neo4j.io → Aura instance → Connect | Graph DB connection |
| `NEO4J_USER` | console.neo4j.io (shown at creation) | Graph DB auth |
| `NEO4J_PASSWORD` | console.neo4j.io (shown once at creation) | Graph DB auth |

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

```bash
# Start dashboard (third terminal, Phase 8+)
cd ~/Developer/Interstellar/dashboard && npm run dev
# → http://localhost:3000
```
