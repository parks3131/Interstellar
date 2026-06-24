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

## Project Structure

```
Interstellar/
├── ingestion/          # TypeScript — webhook handlers, adapters, test scripts
│   └── src/
│       ├── schemas/    # Shared data contracts (IntentObject, ExecutionObject)
│       └── scripts/    # One-off scripts (e.g. testReasoning.ts)
├── reasoning/          # Python FastAPI — the AI reasoning server
│   ├── prompts/        # System prompts fed to the LLM
│   └── models.py       # Pydantic models (Python mirror of TS schemas)
├── shared/
│   └── mock/           # Static test scenarios (no real APIs needed)
└── spec/
    └── SPEC.md         # This file
```

---

## Schemas (the shared language)

Everything in the system is expressed in two core objects.
Defined in: `ingestion/src/schemas/index.ts` and mirrored in `reasoning/models.py`

### IntentObject
Represents what was **planned**. Sourced from Jira or a PRD.

| Field | What it holds |
|---|---|
| `id` | Internal ID e.g. `intent_jira_INT-402` |
| `source_id` | The actual Jira key e.g. `INT-402` |
| `title` | Ticket title |
| `raw_context` | Full ticket description |
| `acceptance_criteria` | Parsed bullet points from the ticket |
| `scoped_services` | Services explicitly in scope e.g. `["payment_service"]` |
| `status` | TODO / IN_PROGRESS / READY_FOR_REVIEW / DONE |
| `owner` | UnifiedUser — who owns this ticket |

### ExecutionObject
Represents what was **built**. Sourced from a GitHub PR or direct push.

| Field | What it holds |
|---|---|
| `id` | Internal ID e.g. `exec_gh_pr_84` |
| `source_id` | PR number or commit SHA |
| `push_type` | `pull_request` or `direct_push` |
| `target_branch` | Which branch was targeted (critical for detecting main pushes) |
| `status` | DRAFT / OPEN / MERGED / CLOSED / DIRECT_PUSH |
| `changeset.impacted_files` | Every file path touched in the PR |
| `changeset.diff_summary` | Human-readable summary of what changed |
| `linked_intent_ids` | Jira keys found in the PR title/body e.g. `["INT-402"]` |
| `author` | UnifiedUser — who wrote the code |

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
| `ingestion/src/schemas/index.ts` | Defines IntentObject, ExecutionObject, DriftAnalysis in TypeScript |
| `reasoning/models.py` | Python (Pydantic) mirror of the same schemas for FastAPI |
| `reasoning/prompts/drift_detection.txt` | System prompt: instructs the LLM to compare intent vs execution and return structured JSON |
| `reasoning/main.py` | FastAPI server — POST /analyze receives an intent+execution pair, calls the LLM via OpenRouter, returns a DriftAnalysis |
| `shared/mock/scenario1_aligned.json` | Test case: coupon code PR that only touches payment_service — should return NONE |
| `shared/mock/scenario2_scope_creep.json` | Test case: same ticket but PR also touches user_auth_service — should return HIGH |
| `shared/mock/scenario3_policy_violation.json` | Test case: critical bug fix pushed directly to main with no PR — should return CRITICAL |
| `ingestion/src/scripts/testReasoning.ts` | Loads all 3 scenarios, fires them at the reasoning server, prints results |

**How to run:**
```bash
# Terminal 1 — start reasoning server
cd reasoning && .venv/bin/uvicorn main:app --reload

# Terminal 2 — run the test
cd ingestion && npm run test:reasoning
```

**Results confirmed:**
- Scenario 1: `drift_detected: false` / `NONE` — passed correctly
- Scenario 2: `drift_detected: true` / `HIGH` — caught scope creep into user_auth_service
- Scenario 3: `drift_detected: true` / `CRITICAL` — caught direct push bypassing PR requirement

**Model:** `openai/gpt-oss-120b` via OpenRouter
**Config:** `reasoning/.env` (never committed — in .gitignore)

---

## Phase 2 — Ingest Adapters (upcoming)

**Goal:** Build the transformation layer that accepts real GitHub and Jira webhook payloads and maps them into IntentObject / ExecutionObject.

**Planned:**
- `transformGitHubPayload(rawPayload)` → ExecutionObject
- `transformJiraPayload(rawPayload)` → IntentObject
- Linking logic: parse PR title/body for Jira keys (regex `/[A-Z]+-\d+/g`) → populate `linked_intent_ids`

---

## Phase 3 — Live Webhook Gateway (upcoming)

**Goal:** Expose real endpoints that receive traffic from GitHub and Jira, run it through the adapters, and trigger the reasoning engine.

**Planned:**
- Express server with POST routes for GitHub and Jira webhooks
- ngrok / Localtunnel to expose local server for testing
- End-to-end run: open a real PR with a Jira key in the title → reasoning fires → drift result logged
