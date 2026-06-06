# AI Warehouse Replenishment Orchestration Demo

> A reference implementation for governed, human-in-the-loop warehouse
> replenishment using **Copilot Studio**, **Microsoft Foundry**, **Databricks**,
> and **Dynamics 365 (D365)**.

The demo shows how a planner can ask a conversational assistant for min/max
replenishment recommendations, see the reasoning and source citations behind
each one, and **approve or reject** every change before anything is written back
to D365. It runs **fully self-contained in `MOCK_MODE`** — no cloud credentials
required — so you can clone it and have the whole experience running locally.

---

## Architecture at a glance

```
┌──────────────────────┐     ┌──────────────────────────┐     ┌─────────────────────┐
│  Copilot Studio       │     │  Microsoft Foundry        │     │  Systems of record   │
│  (conversation +      │ ──▶ │  agents + workflows       │ ──▶ │  Databricks (signals)│
│   approval cards)     │     │  retriever │ validator │  │     │  D365 (orders/waves, │
│                       │ ◀── │  recommender │ writer    │ ◀── │  min/max write-back) │
└──────────────────────┘     └──────────────────────────┘     └─────────────────────┘
            ▲                              ▲
            │        FastAPI service       │
            └──────── (src/app) ───────────┘
                    React + Vite UI (frontend/)
```

- **Retriever** pulls replenishment candidates from Databricks signals.
- **Validator** blocks any SKU that is on an active D365 wave (deterministic governance gate).
- **Recommender** reasons over each candidate and emits a decision with citations and a confidence score.
- **Writer** is the *only* agent allowed to mutate D365 — and only after explicit human approval.
- The **orchestrator** runs cross-facility planning and produces a ranked action plan.

See [docs/01-architecture.md](docs/01-architecture.md) for the full picture.

---

## Quickstart (MOCK_MODE)

### Backend — FastAPI service

```bash
uv sync
uv run uvicorn app.main:app --app-dir src --reload --port 8080
```

Then:

```bash
curl http://localhost:8080/health
curl "http://localhost:8080/recommendations/sequential?facility=NJ-01"
```

### Frontend — React + Vite

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (proxies /api → :8080)
```

### Everything at once — start script

```bash
./start.sh          # mock mode (default) — fully offline
./start.sh --live   # live Foundry reasoning (see "Two Foundry modes" below)
```

### Everything at once — Docker Compose

```bash
docker compose up --build
# backend  → http://localhost:8080
# frontend → http://localhost:5173
```

---

## Repository layout

```
src/
  app/              FastAPI service (routes, services, mocks, schemas)
  foundry/          Agents, workflows, prompts, evaluations
data/               Deterministic mock data pack (Databricks + D365 JSON)
frontend/           React + TypeScript + Vite UI
copilot-studio/     Importable Copilot Studio solution (topics, actions, cards)
infra/              Bicep (Foundry/KV/Log Analytics), Databricks + CI notes
notebooks/          Databricks SQL for min/max candidate generation
tests/              unit / integration / evaluation harness
docs/               Architecture, user guide, data contracts, governance
```

---

## Mock mode vs. production

`MOCK_MODE=true` (the default) makes the demo deterministic and offline:

- Databricks and D365 clients read the JSON data pack in [data/](data).
- Foundry workflows run locally, in-process — no model deployment needed.

### Two Foundry modes

**Databricks and D365 are always mocked** from the data pack. Only the Foundry
*reasoning narration* has two modes, selectable from the header toggle in the UI
or via `FOUNDRY_MODE`:

| Mode | Behavior | Requirements |
| --- | --- | --- |
| **Mock** (default) | Deterministic local templates write the explanation. Fully offline. | None |
| **Live** | A real Azure AI Foundry model writes the explanation; data/Databricks/D365 stay mocked. | `AZURE_FOUNDRY_PROJECT_ENDPOINT` + `az login` |

The **decision, citations, and numbers are deterministic in both modes** — only
the natural-language wording changes, and `reject` cases never call the model.
That keeps evaluations mode-independent and governance intact.

To enable live Foundry:

```bash
uv pip install -r requirements-prod.txt   # azure-ai-projects, azure-identity, openai
# set AZURE_FOUNDRY_PROJECT_ENDPOINT in .env, then:
az login
./start.sh --live
```

`/health` reports the active `foundry_mode` and whether `foundry_live_available`,
which the UI uses to enable/disable the Live toggle.

### Real Databricks / D365

To wire the real data systems, set `MOCK_MODE=false`, populate the variables in
[.env.example](.env.example), and install the production dependencies:

```bash
uv pip install -r requirements-prod.txt
```

Those packages (Agent Framework, `azure-ai-projects`, Databricks SQL connector)
currently ship as pre-releases, so they are intentionally kept out of the default
install to keep the demo reproducible. Production code paths are stubbed and
documented inline in [src/app/services/](src/app/services).


---

## Governance highlights

- **Human-in-the-loop by design.** No min/max change reaches D365 without an explicit approval action.
- **Deterministic guardrail.** SKUs on an active wave are rejected by the validator before reasoning — not left to the model.
- **Grounded recommendations.** Every recommendation carries `databricks://` and `d365://` citations; recommended values are never fabricated by the reasoner.
- **Auditable writes.** Each approved write returns an audit id.
- **Continuous evaluation.** Groundedness and decision-quality checks run in CI via the eval harness.

See [docs/04-governance.md](docs/04-governance.md) for details.

---

## Testing & evaluation

```bash
uv run ruff check .                      # lint
uv run pytest -q                         # unit + integration tests
uv run python -m tests.evals.run_evals   # groundedness + decision-quality evals
```

CI runs the same steps plus the frontend build — see [.github/workflows/ci.yml](.github/workflows/ci.yml).

---

## Documentation

| Doc | Topic |
| --- | --- |
| [docs/01-architecture.md](docs/01-architecture.md) | System architecture and agent roles |
| [docs/02-user-guide.md](docs/02-user-guide.md) | Step-by-step install, run, and usage guide |
| [docs/03-data-contracts.md](docs/03-data-contracts.md) | Schemas and the mock data pack |
| [docs/04-governance.md](docs/04-governance.md) | Approval flow, guardrails, auditability |
| [docs/05-copilot-studio.md](docs/05-copilot-studio.md) | Copilot Studio topics, actions, cards |
| [docs/06-foundry.md](docs/06-foundry.md) | Foundry agents, workflows, evaluations |
| [docs/07-demo-options.md](docs/07-demo-options.md) | Sequential vs. multi-agent options with sequence diagrams |
| [docs/08-copilot-studio-setup.md](docs/08-copilot-studio-setup.md) | Step-by-step Copilot Studio + Foundry setup runbook |

---

## License

[MIT](LICENSE)
