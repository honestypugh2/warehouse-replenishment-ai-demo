# 04 — Governance & Security

Five control points keep updates to D365 safe, governed, and auditable.

| # | Control | How it works | Outcome |
| --- | --- | --- | --- |
| 1 | **Least-privilege access** | Agents and services use managed identities with scoped permissions to Databricks and D365 (MCP/DMF). | Minimizes over-permissioned access. |
| 2 | **Data validation (check before write)** | The Operational Validator checks open orders, active waves, and capacity. | Prevents updates that cause disruption or extra cost. |
| 3 | **Human approval (mandatory gate)** | Copilot Studio shows Adaptive Cards with recommendations, rationale, and citations. A human must approve. | Humans remain in control of every D365 update. |
| 4 | **Controlled write (writer agent only)** | Only the D365 Writer agent performs writes, and only after approval. | A single controlled pathway for all data changes. |
| 5 | **Audit & traceability (end-to-end)** | Every step is logged with prompt, data sources, decision, approver, and write result. | Complete audit trail for compliance and review. |

## Identity

- **Entra ID end-to-end.** Copilot Studio inherits M365/Entra controls.
- **Per-agent managed identity** in Foundry with least-privilege scopes.
- **MCP tool allow-lists** restrict what the writer can call.

## Validation is deterministic

Operational validation is implemented in code
([`src/foundry/agents/validator_agent.py`](../src/foundry/agents/validator_agent.py)), not
left to the LLM. The LLM explains *why* a rule fired; the rule itself is testable
and versioned. This is the trust boundary in front of D365.

## Audit record (per write)

Each approved write captures:

- the originating prompt,
- the retrieved Databricks candidate rows,
- the validator output (pass/fail + blocking evidence),
- the decision and the approver UPN,
- the write result and `audit_id`.

Traces are emitted as OpenTelemetry GenAI spans and persisted to Log Analytics
(provisioned in [`infra/bicep/main.bicep`](../infra/bicep/main.bicep)).

## Data governance

- Databricks Unity Catalog permissions stay in place; the backend only reads.
- Purview labels/lineage propagate from Databricks sources.
- Secrets (D365 / Databricks) live in Key Vault; no secrets in source.

## Separation of ownership

| Layer | Owner | Where |
| --- | --- | --- |
| Topics, prompts, approval logic | Business-apps team | Copilot Studio solution |
| Workflow + agents | Data / IT team | `src/foundry/` (versioned in GitHub) |
| Candidate logic + tables | Data team | Databricks (Unity Catalog) |
| Stocking-limit master + execution | Operations / ERP team | D365 F&O |
