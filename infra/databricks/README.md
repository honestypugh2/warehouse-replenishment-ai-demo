# Databricks setup (system of intelligence)

The demo consumes Databricks; it does not replace it. For production wiring:

1. **SQL Warehouse** — create (or reuse) a serverless SQL Warehouse. Note the
   `warehouse_id` and HTTP path for `src/app/services/databricks_client.py`.
2. **Candidate logic** — deploy [`notebooks/01_min_max_candidates.sql`](../../notebooks/01_min_max_candidates.sql)
   as a scheduled job (or materialized view) that writes
   `main.replen.min_max_candidates` daily.
3. **Read access** — grant a service principal (or the backend's managed
   identity) read-only access to the candidate + operational tables via Unity
   Catalog.
4. **Governance** — keep Unity Catalog permissions and Purview lineage in place.
   The backend only reads; it never writes back to Databricks.

## Tables referenced by the candidate query

| Table | Role |
| --- | --- |
| `main.replen.shipments_daily` | Historical shipments per SKU/facility |
| `main.replen.inventory_snapshot` | On-hand by location |
| `main.replen.location_capacity` | Slot capacity / class |
| `main.replen.stocking_limits` | Current min/max (mirrored from D365) |
| `main.replen.min_max_candidates` | Output consumed by the Retriever agent |
