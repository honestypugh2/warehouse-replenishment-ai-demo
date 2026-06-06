# 02 — User Guide

A step-by-step guide to installing, running, and using the AI Warehouse
Replenishment Orchestration Demo. The demo runs **fully offline in `MOCK_MODE`**
by default, so you can complete every step below without any cloud credentials.

> Companion docs: [01 — Architecture](01-architecture.md),
> [03 — Data contracts](03-data-contracts.md),
> [04 — Governance](04-governance.md),
> [07 — Demo options](07-demo-options.md),
> [08 — Copilot Studio + Foundry setup](08-copilot-studio-setup.md).

---

## 1. Prerequisites

| Tool | Why | Check |
| --- | --- | --- |
| **Python 3.13** | Backend (FastAPI service + agents) | `python3 --version` |
| **[uv](https://docs.astral.sh/uv/)** | Python env + dependency manager | `uv --version` |
| **Node.js 18+** & npm | React + Vite frontend | `node --version` |
| **Azure CLI** (`az`) *(live mode only)* | Auth to Azure AI Foundry | `az version` |
| **Azure Developer CLI** (`azd`) *(live mode only)* | Provision Foundry + App Insights | `azd version` |

You only need `az` and `azd` if you plan to run **live Foundry** mode (Section 6).
Everything else works offline.

---

## 2. Install

Clone the repo, then install backend and frontend dependencies:

```bash
git clone <repo-url> warehouse-replenishment-ai-demo
cd warehouse-replenishment-ai-demo

# Backend: create the virtual environment and install dependencies
uv sync

# Frontend: install Node packages
cd frontend && npm install && cd ..
```

`uv sync` creates a `.venv/` and installs the locked dependencies from
`uv.lock`. The `start.sh` script will also run `npm install` automatically the
first time if you skip it here.

---

## 3. Run the demo (mock mode)

The simplest path launches both services with one command:

```bash
./start.sh
```

This starts:

- **Backend** → http://localhost:8080 (API docs at http://localhost:8080/docs)
- **Frontend** → http://localhost:5173

To stop everything:

```bash
./stop.sh
```

### Run the services manually (optional)

If you prefer two terminals instead of `start.sh`:

```bash
# Terminal 1 — backend
uv run uvicorn app.main:app --app-dir src --reload --port 8080

# Terminal 2 — frontend
cd frontend && npm run dev
```

### Confirm it's healthy

```bash
curl http://localhost:8080/health
```

You should see `ok: true` and `foundry_mode: "mock"`. The UI header also shows
the active Foundry mode.

---

## 4. Use the web app

Open http://localhost:5173. The UI has two main tabs.

### Sequential review (Option A)

A deterministic, audit-friendly pipeline:
**Retriever → Validator → Recommender → Approval gate → Writer**.

1. Select a facility — start with **`NJ-01`**.
2. Click **Run daily replen review**.
3. The summary shows the candidate count and how many passed vs. were blocked
   (e.g. *12 candidates · validated · 2 blocked*).
4. Inspect each card:
   - **Decision pill** — `approve`, `needs_review`, or `reject`.
   - **Citations** — every card cites its Databricks signal and D365 record, so
     the numbers are grounded, never invented.
   - **Blocked cards** show the validator's evidence (the active wave id and open
     orders that caused the block).
5. On a card you agree with, click **Approve** → the change is written to D365
   (mock) and returns an **audit id**.
6. On a `needs_review` card, click **Reject / Defer** and add a reason — that's
   logged too.

> **Governance:** Nothing reaches D365 without an explicit approval action, and
> SKUs on an active wave are blocked **before** reasoning. See
> [04 — Governance](04-governance.md).

### Multi-agent plan (Option B)

Cross-facility planning by a small team of specialist agents:

1. Switch to the **Multi-agent plan** tab.
2. Select one or more facilities (e.g. **`NJ-01`** and **`CA-02`**).
3. Click **Plan cross-facility changes**.
4. Review the ranked table — each row carries its own rationale, citations, and
   a decision pill.
5. Click **Bulk-approve high-confidence** to approve the high-confidence set in
   one action (still human-gated, still audited).

---

## 5. Use the API directly (optional)

Every UI action maps to a REST endpoint. Examples (mock mode):

```bash
# Sequential review for one facility
curl "http://localhost:8080/recommendations/sequential?facility=NJ-01"

# Multi-agent plan across facilities
curl "http://localhost:8080/recommendations/multiagent?facilities=NJ-01,CA-02"

# Validate a single SKU
curl "http://localhost:8080/validate?facility=NJ-01&sku=CHARD-750-12"

# Approve a change (the only path that writes to D365)
curl -X POST http://localhost:8080/approve \
  -H "Content-Type: application/json" \
  -d '{"sku":"CHARD-750-12","facility":"NJ-01","new_min":100,"new_max":320,
       "approver_upn":"planner@contoso.com","rationale":"Within wave window"}'
```

Append `&foundry=live` to a GET request to force live reasoning for that call
without restarting (see Section 6). Full schemas are in
[03 — Data contracts](03-data-contracts.md), and the interactive API explorer is
at http://localhost:8080/docs.

---

## 6. Run with live Foundry (optional)

In live mode, a real Azure AI Foundry model writes the natural-language
explanation. **Databricks and D365 stay mocked**, and the decision, citations,
and numbers remain deterministic — only the wording changes, and `reject` cases
never call the model.

### One-time setup

```bash
# 1. Install the live dependencies (Agent Framework, azure-ai-projects, openai)
uv pip install -r requirements-prod.txt

# 2. Sign in to Azure
az login

# 3. Provision the Foundry project + Application Insights (writes .azure/<env>/.env)
azd provision

# 4. Provision the persistent Foundry agents so they appear in the portal
uv run python scripts/provision_foundry_agents.py
```

### Launch in live mode

```bash
./start.sh --live
```

`start.sh --live` automatically loads the azd outputs from `.azure/<env>/.env`
(the Foundry endpoint, the Application Insights connection string, and
`FOUNDRY_USE_AGENTS=true`), so the persistent agents and tracing light up.

### Verify live mode

```bash
curl http://localhost:8080/health
```

Look for `foundry_mode: "live"`, `foundry_use_agents: true`, and
`tracing_enabled: true`. In the UI, the **Live** toggle in the header becomes
available; recommendation narration is now model-generated.

Agent activity (`invoke_agent`, `chat`, and `workflow.run` spans) flows to
Application Insights. See [06 — Foundry](06-foundry.md) for the tracing details.

---

## 7. Test & evaluate

```bash
uv run ruff check .                      # lint
uv run pytest -q                         # unit + integration tests
uv run python -m tests.evals.run_evals   # groundedness + decision-quality evals
```

CI runs the same steps plus the frontend build — see
[.github/workflows/ci.yml](../.github/workflows/ci.yml).

---

## 8. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Virtual environment not found at .venv` | Run `uv sync` before `./start.sh`. |
| Port 8080 or 5173 already in use | Run `./stop.sh` (it frees both ports), then start again. |
| Frontend can't reach the API | Confirm the backend is up: `curl http://localhost:8080/health`. The Vite dev server proxies `/api` → `:8080`. |
| Live toggle is disabled in the UI | You're in mock mode, or `foundry_live_available` is false. Complete Section 6 and relaunch with `./start.sh --live`. |
| Agents don't appear in the Foundry portal | Run `uv run python scripts/provision_foundry_agents.py`, then relaunch with `./start.sh --live`. |
| No traces in Application Insights | Ensure `azd provision` populated `.azure/<env>/.env` with `APPLICATIONINSIGHTS_CONNECTION_STRING`; `start.sh --live` sources it automatically. |
| Logs | `tail -f logs/backend.log` and `tail -f logs/frontend.log`. |

---

## Next steps

- [01 — Architecture](01-architecture.md) — the mental model and component map.
- [07 — Demo options](07-demo-options.md) — sequential vs. multi-agent patterns.
- [08 — Copilot Studio + Foundry setup](08-copilot-studio-setup.md) — publish the
  assistant to Teams via Copilot Studio.
