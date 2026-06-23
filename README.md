# Interstellar

Interstellar is a developer intelligence platform that connects your existing tools — Jira, Slack, GitHub, Figma, and Docs — and reasons across them to surface drift, generate agent-ready specs, and keep what was intended aligned with what gets built.

---

## Core flow

```
Ingest → Reason → [Flag or Spec] → Agent executes
```

---

## How it works

### 1. Ingest
Interstellar connects directly to your tools and continuously pulls context:

| Source | What it captures |
|---|---|
| **Jira** | Tickets, epics, acceptance criteria, scope |
| **Slack** | Decisions, async discussions, clarifications |
| **GitHub** | Commits, PR diffs, codebase state |
| **Figma** | Design intent, component specs |
| **Docs / PRDs** | Written specs, RFCs, requirements |

---

### 2. Reason
The reasoning layer is the core of Interstellar. It holds two pictures in context simultaneously and compares them:

- **What was supposed to be built** — derived from Jira, PRD, Slack decisions, Figma
- **What is actually being built** — derived from GitHub commits, PR diffs, codebase

This is not document retrieval. The reasoner actively compares intent against reality and forms a judgment about whether they match.

---

### 3. Flag (when there's drift)
When reasoning finds a gap between intent and reality, it produces a **flag** — a specific, scoped signal surfaced to the engineering team before it becomes a broken sprint.

Example:
> "The Jira ticket scoped this to the payments service only, but the PR is touching the user auth flow too — that's outside spec."

Flags are the output of reasoning when the answer to *"do these match?"* is **no**. Drift detection is not a separate module — it is what reasoning produces when a gap is found.

---

### 4. Spec (when things are aligned)
Once a flag is cleared — or if reasoning finds no drift — Interstellar generates a **spec**: a structured file an agent can actually execute.

A spec is not a reformatted Jira ticket. It contains:
- What to build and why
- Relevant codebase context and patterns
- Acceptance criteria and definition of done
- Past decisions from Slack and Docs
- What to avoid

The spec is trustworthy because it was produced by reasoning across all context, not assembled from a single source.

---

### Full sequence in practice

```
1. Reasoning reads across all tool context
2. If drift is found → flag surfaced to engineering team
3. Flag is cleared (or no drift found) → spec is generated
4. Agent picks up the spec and executes
```

---

## Deployment scenarios

### Scenario A — Built on an existing context layer
Interstellar connects to an external vendor (Glean, Unblocked, Onyx) via MCP / API. The vendor handles ingestion, indexing, and permissions. Interstellar adds the reasoning, flagging, and spec generation on top.

- Lower build effort
- Depends on vendor ingestion quality
- Less control over what gets indexed

### Scenario B — Owns the full stack
Interstellar handles everything: direct API connectors per tool, its own ingestion engine, a context engine (semantic graph, indexing, memory), and the reasoning layer on top.

- Full control and customization
- No vendor dependency
- Significantly more to build and maintain
