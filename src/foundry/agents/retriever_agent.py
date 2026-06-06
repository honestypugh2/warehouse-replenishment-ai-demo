"""Retriever agent — pulls candidate min-max rows from Databricks.

Tool: Databricks SQL Warehouse. The retriever never invents numbers; it only
surfaces the candidates produced by the daily Databricks job.
"""

from __future__ import annotations

from app.models.schemas import Candidate
from app.services.databricks_client import DatabricksClient


def retrieve(facility: str) -> list[Candidate]:
    rows = DatabricksClient().get_candidates(facility)
    return [Candidate(**row) for row in rows]
