# 03 — Data Contracts

The schemas the backend, frontend, and Copilot Studio actions share. Source of
truth: [`src/app/models/schemas.py`](../src/app/models/schemas.py) (Pydantic) and
[`frontend/src/types.ts`](../frontend/src/types.ts) (TypeScript).

## Databricks → backend (candidate)

Produced by [`notebooks/01_min_max_candidates.sql`](../notebooks/01_min_max_candidates.sql);
served in mock mode from [`data/candidates.json`](../data/candidates.json).

| Field | Type | Notes |
| --- | --- | --- |
| `sku` | string | e.g. `CAB-750-12` |
| `facility` | string | e.g. `NJ-01` |
| `location` | string | pick-module slot, e.g. `PM-A12` |
| `current_min` / `current_max` | int | current D365 stocking limits |
| `recommended_min` / `recommended_max` | int | Databricks candidate values (never altered by the LLM) |
| `rationale` | string | short, human-readable reason |
| `confidence` | float 0–1 | drives the decision policy |

## D365 reads (validation inputs)

- **Active waves** — [`waves.json`](../data/waves.json): `wave_id`,
  `facility`, `status`, `skus[]`.
- **Open orders** — [`orders.json`](../data/orders.json): `order_id`,
  `sku`, `facility`, `qty`, `status`.
- **Capacity** — [`capacity.json`](../data/capacity.json): `location`,
  `facility`, `max_units`, `slot_class`.

## Backend outputs

### `Recommendation`
`candidate` + `validation` + `decision` (`approve_suggested` | `needs_review` |
`reject`) + `explanation` + `citations[]`.

### Decision policy
- `reject` — validator failed (e.g. active-wave conflict).
- `approve_suggested` — validator passed **and** `confidence ≥ 0.80`.
- `needs_review` — validator passed **and** `confidence < 0.80`.

### `D365WriteResponse`
`sku`, `facility`, `success`, `audit_id`, `message`.

## Citation scheme

Every recommendation traces back to its sources:

- `databricks://candidates/{facility}/{sku}`
- `d365://waves/{facility}` and `d365://waves/{wave_id}`
- (production) `policy://{doc}#{section}` for SOP grounding

## REST endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness + mock-mode flag |
| GET | `/recommendations/sequential?facility=` | Option A run |
| GET | `/recommendations/multiagent?facilities=&facilities=` | Option B run |
| GET | `/validate?facility=&sku=` | Single-SKU validator evidence |
| GET | `/d365/orders?sku=` | Open orders for a SKU |
| GET | `/d365/waves?facility=` | Active waves for a facility |
| POST | `/approve` | Human approval → D365 write |
| POST | `/approve/reject` | Deferral with reason |

## D365 write path (production)

Performed only after approval, by the Writer agent, through either an MCP server
for D365 or the F&O Data Management Framework (DMF) entity for stocking limits
(e.g. `InventStockingLimits`). Every call is logged with an audit id.
