# Interstellar

Interstellar is a developer intelligence platform that connects your existing tools — Jira, Slack, GitHub, and Docs — and reasons across them to surface context, detect drift, and generate agent-ready specs.

## What it does

| Component | Description |
|---|---|
| **Reasoner** | Synthesizes signals across all connected tools into a single coherent view |
| **Drift detector** | Identifies gaps between original intent and what was actually built |
| **Spec generator** | Produces structured, agent-ready artifacts from cross-tool context |

Outputs are delivered to both **engineering teams** and **AI agents**.

## Architecture

Interstellar supports two deployment scenarios:

### Scenario A — Built on an existing context layer
Connects to an external vendor (Glean, Unblocked, Onyx) via MCP / API. The vendor handles ingestion, indexing, and permissions. Interstellar sits on top and adds reasoning, drift detection, and spec generation.

- Lower build effort
- Depends on vendor ingestion quality
- Less control over what gets indexed

### Scenario B — Owns the full stack
Interstellar handles everything: direct API connectors to each tool, its own ingestion engine, a context engine (semantic graph, indexing, memory), and the reasoning layer on top.

- Full control and customization
- No vendor dependency
- Significantly more to build and maintain

## Connected tools

- **Jira** — tickets, epics, intent
- **Slack** — discussions, decisions, async context
- **GitHub** — code, PRs, reviews, actual build state
- **Docs** — specs, RFCs, design documents
