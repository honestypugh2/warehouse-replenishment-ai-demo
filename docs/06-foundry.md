# 06 — Foundry Design Guidance

Microsoft Foundry (Azure AI Foundry) is the **engine**: it hosts the workflow and
agents built with the Microsoft Agent Framework. See [`src/foundry/`](../src/foundry).

## Two runtime modes

The data systems (**Databricks** and **D365**) are **always mocked** from the
deterministic data pack in [`data/`](../data). Only the *reasoning narration*
swaps between two modes:

| Mode | What runs | Requirements |
| --- | --- | --- |
| **Mock** (`FOUNDRY_MODE=mock`, default) | Deterministic local templates produce the explanation. Fully offline. | None |
| **Live** (`FOUNDRY_MODE=live`) | A real Azure AI Foundry model writes the explanation. | `AZURE_FOUNDRY_PROJECT_ENDPOINT` + `az login` (or managed identity) |

Critically, the **decision** (`approve_suggested` / `needs_review` / `reject`),
the **citations**, and the **numbers** are deterministic in *both* modes — only
the natural-language explanation differs. `reject` candidates always use the
deterministic template and never call the model. This keeps the evaluation
harness mode-independent and preserves governance.

The React app exposes a **Mock / Live Foundry** toggle in the header (Live is
disabled until the server reports `foundry_live_available`). The choice is sent
per request via the `foundry` query parameter; the server only honors `live`
when Foundry is actually configured.

## Sequential pattern (Option A)

A single Agent Framework `SequentialOrchestration`:

```
Retriever → Validator → Reasoner → Approval gate → Writer → Auditor
```

Each step is an agent with a tight system prompt
([`src/foundry/prompts/`](../src/foundry/prompts)) and a single tool. The workflow emits
OpenTelemetry GenAI traces persisted to Log Analytics.

## Multi-agent pattern (Option B)

An **orchestrator agent** delegates to specialists and consolidates a ranked
plan. Use **handoff** for branching (e.g. validator rejects → hand to the Risk
Reasoner) and **concurrent** for per-facility parallelism. A shared scratchpad
holds short-term memory. Only the Writer may touch D365.

## Agent responsibilities

| Agent | Owns | Tools |
| --- | --- | --- |
| Retriever | Pull candidate rows | Databricks SQL Warehouse |
| Slotting Analyst | Reason about locations/capacity | Databricks tables, slot geometry |
| Demand Forecaster | Velocity / forecast deltas | Databricks history |
| Validator | Check live D365 state | D365 read (OData / MCP) |
| Risk/Policy Reasoner | Apply business rules | Policy doc (Azure AI Search) |
| Writer | The only D365 mutator | D365 MCP server / DMF |
| Auditor | Persist decisions + rationale | Log Analytics / Fabric |

## Grounding / retrieval

- **Primary:** structured Databricks tables via SQL Warehouse (deterministic).
- **Secondary:** policy / SOP documents indexed in Azure AI Search behind a
  Foundry knowledge tool.
- Always return **citation ids** (`databricks://…`, `d365://…`, `policy://…`).

## Validation logic

Keep operational validation deterministic (D365 reads + Python rules), not
LLM-only. The LLM explains *why* a rule fired; the rule itself is code, encoded
and reviewed in [`src/foundry/agents/validator_agent.py`](../src/foundry/agents/validator_agent.py).

## Trustworthy & auditable outputs

- Mandatory **approval gate** before any write.
- **Evaluation harness** ([`src/foundry/evaluations/`](../src/foundry/evaluations)):
  groundedness + decision-quality run in CI before each release.
- **OTel GenAI tracing** + audit log with prompt, retrieved rows, validator
  output, decision, approver UPN, and write result.
- Per-agent **managed identity** with least-privilege scopes (MCP allow-lists).

## Production wiring

The mock workflows mirror the production shape.

**Live Foundry (reasoning only).** This path is already implemented in
[`src/foundry/foundry_reasoner.py`](../src/foundry/foundry_reasoner.py) and
[`src/foundry/narration.py`](../src/foundry/narration.py):

1. `uv pip install -r requirements-prod.txt` (installs `azure-ai-projects`,
   `azure-identity`, `openai`).
2. Set `AZURE_FOUNDRY_PROJECT_ENDPOINT` (and optionally
   `AZURE_FOUNDRY_MODEL_DEPLOYMENT`, `AZURE_FOUNDRY_API_VERSION`) in `.env`.
3. `az login` (auth uses `DefaultAzureCredential` — no keys).
4. Start in live mode: `./start.sh --live` (or `FOUNDRY_MODE=live`), or flip the
   toggle in the UI.

The live reasoner imports are **lazy**, so the mock demo never needs the
production packages installed.

**Live Databricks / D365.** Still mocked in this demo. Replace the mock clients
in [`src/app/mocks`](../src/app/mocks) with real Databricks SQL / D365 MCP
clients. (The Microsoft Agent Framework currently ships as a pre-release — pin to
the latest stable once published.)
