"""Validation endpoint — exposes the Operational Validator independently.

Useful for the ``ExplainRejection`` Copilot Studio topic, which needs the
validator's evidence (blocking wave id, open orders) for a single SKU.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import Candidate, ValidationResult
from app.services.databricks_client import DatabricksClient
from foundry.agents.validator_agent import validate

router = APIRouter(prefix="/validate", tags=["validate"])


@router.get("", response_model=ValidationResult)
def validate_sku(
    facility: str = Query(..., examples=["NJ-01"]),
    sku: str = Query(..., examples=["CAB-750-12"]),
) -> ValidationResult:
    rows = DatabricksClient().get_candidates(facility)
    row = next((r for r in rows if r["sku"] == sku), None)
    if row is None:
        raise HTTPException(404, f"No candidate found for {sku} at {facility}.")
    return validate(Candidate(**row))
