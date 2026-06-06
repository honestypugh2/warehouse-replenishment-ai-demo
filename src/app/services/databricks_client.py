"""Databricks SQL Warehouse client.

Databricks is the *system of intelligence*: it owns the daily min-max candidate
logic and historical velocity. In MOCK_MODE we read the synthetic data pack; in
production we query the SQL Warehouse with a managed identity.
"""

from __future__ import annotations

from app.config import settings
from app.mocks import databricks_mock


class DatabricksClient:
    def __init__(self) -> None:
        self.mock = settings.mock_mode

    def get_candidates(self, facility: str) -> list[dict]:
        if self.mock:
            return databricks_mock.candidates(facility)
        # --- PRODUCTION ---------------------------------------------------
        # from databricks import sql
        # with sql.connect(
        #     server_hostname=settings.databricks_host,
        #     http_path=settings.databricks_http_path,
        #     access_token=settings.databricks_token,  # prefer managed identity
        # ) as conn, conn.cursor() as cur:
        #     cur.execute(
        #         "SELECT * FROM main.replen.min_max_candidates WHERE facility = ?",
        #         [facility],
        #     )
        #     cols = [d[0] for d in cur.description]
        #     return [dict(zip(cols, row)) for row in cur.fetchall()]
        raise NotImplementedError("Wire the Databricks SQL Warehouse here.")

    def get_history(self, sku: str) -> dict:
        if self.mock:
            return databricks_mock.history(sku)
        raise NotImplementedError("Wire the Databricks history query here.")
