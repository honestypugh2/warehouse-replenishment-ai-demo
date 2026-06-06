# Copilot Studio Solution — Replenishment Assistant

This folder is an importable Copilot Studio solution package. Copilot Studio is
the **main entry point**: the business-user surface that routes prompts, surfaces
approval cards, and calls the governed Foundry workflow (persistent agents
`replen-retriever` / `replen-validator` / `replen-recommender`).

> Full integration guide, architecture diagram, auth, and troubleshooting:
> [`docs/05-copilot-studio.md`](../docs/05-copilot-studio.md).

## Example prompt

> **"Show today's replenishment recommendations for the New Jersey facility."**

Flow: generative orchestration → resolve `New Jersey → NJ-01` → REST API tool
`runSequential` (`GET /recommendations/sequential?facility=NJ-01`) → backend runs
the Foundry sequential workflow → Adaptive Cards render **SKU, location, current
min/max, suggested min/max, confidence, active-wave warning, decision,
explanation, citations**. Rejected SKUs (active wave) show **no** approve button.

## Contents

| Path | Purpose |
| --- | --- |
| [solution.yaml](solution.yaml) | Importable solution manifest (agent, topics, actions, cards). |
| `topics/` | Conversation topics (entry, explain, approve, cross-facility). |
| `actions/` | OpenAPI v2 definitions exposed as **REST API tools** that call the backend / Foundry. |
| `adaptive-cards/` | Approval and rejection Adaptive Cards rendered in Teams. |

> Copilot Studio renamed **Actions → Tools** (April 2025+). This package's
> `actions/*.json` are imported as **REST API tools** in the current UI.

## Import & bind

1. **Import** — Copilot Studio → *Solutions* → *Import solution* → upload
   `solution.yaml` (or the exported `.zip`). Review and import.
2. **REST API tools** — import `actions/call-foundry-sequential.json` and
   `actions/call-foundry-multiagent.json` (OpenAPI v2 JSON). Point the `host`
   at your backend (the FastAPI service or the Foundry-fronting endpoint).
3. **Secure the tools** — choose one:
   - **API key** (simplest): Parameter name `code`, location **Query** (function key).
   - **OAuth 2.0** (production): your Entra ID app's authorization/token URLs and
     scope `api://<APP_ID>/.default`. Authorize the Copilot Studio first-party app
     `38e2b35e-2ae8-48c9-9c8a-cb0a1ba27cdc` and restrict to *My organization only*.
4. **Environment variables** — set `API_BASE_URL`,
   `FOUNDRY_SEQUENTIAL_ENDPOINT`, `FOUNDRY_MULTIAGENT_ENDPOINT`, and
   `TEAMS_APPROVAL_WEBHOOK` for your environment.
5. **Publish** — publish to the Microsoft Teams channel (primary). Web chat is
   optional.

## Topic → backend mapping

| Topic | Tool · operation | Backend endpoint |
| --- | --- | --- |
| `GetReplenRecommendations` | `call-foundry-sequential` · `runSequential` | `GET /recommendations/sequential` |
| `ExplainRejection` | `call-foundry-sequential` · `validateSku` | `GET /validate` |
| `ApproveMinMax` | `call-foundry-sequential` · `approve` | `POST /approve` |
| `PlanCrossFacility` | `call-foundry-multiagent` · `runMultiAgent` | `GET /recommendations/multiagent` |

## Design principles

- Keep topic logic small; push reasoning to Foundry.
- The agent **never** writes to D365 directly — only the Foundry writer agent
  does, and only after explicit human approval.
- Always present rationale and citation ids from the workflow response.
- **Alternative (Path B):** instead of the REST API tool you can add the Foundry
  agent natively via **Tools → Add a tool → Azure AI Foundry agent** (project
  `replen-project`). Keep approvals/writes flowing through `/approve`.
- REST API tool and native Foundry agent tool are evolving Copilot Studio
  features (REST API tool in preview) — review data flows and security per
  Microsoft guidance before production use.
