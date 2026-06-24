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
│   ├── adapters/           # Phase 2 — GitHub and Jira payload transformers
│   ├── scripts/
│   │   └── test_scenarios.py    # Runs all 3 mock scenarios against the server
│   ├── requirements.txt
│   ├── .env                # Secret keys — never committed
│   └── .env.example        # Template showing what keys are needed
├── shared/
│   └── mock/               # Static test scenarios (no real APIs needed)
│       ├── scenario1_aligned.json
│       ├── scenario2_scope_creep.json
│       └── scenario3_policy_violation.json
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

## Phase 2 — Ingest Adapters (upcoming)

**Goal:** Build the transformation layer that accepts real GitHub and Jira webhook payloads and maps them into IntentObject / ExecutionObject.

**Planned files:**
- `reasoning/adapters/github.py` — `transform_github_payload(raw)` → ExecutionObject
- `reasoning/adapters/jira.py` — `transform_jira_payload(raw)` → IntentObject
- Linking logic: parse PR title/body for Jira keys using regex `[A-Z]+-\d+` → populate `linked_intent_ids`

---

## Phase 3 — Live Webhook Gateway (upcoming)

**Goal:** Expose real endpoints that receive traffic from GitHub and Jira, run it through the adapters, and trigger the reasoning engine.

**Planned:**
- Add POST /ingest/github and POST /ingest/jira routes to `main.py`
- ngrok / Localtunnel to expose local server for testing
- End-to-end run: open a real PR with a Jira key in the title → reasoning fires → drift result logged
