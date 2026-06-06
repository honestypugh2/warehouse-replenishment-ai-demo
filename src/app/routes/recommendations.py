"""Recommendation endpoints — drive the Foundry sequential / multi-agent flows."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.models.schemas import MultiAgentRunResult, SequentialRunResult
from app.services.foundry_client import FoundryClient

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

FoundryMode = Literal["mock", "live"]


def _check_live(mode: str | None) -> None:
    if mode == "live" and not settings.foundry_live_available:
        raise HTTPException(
            status_code=400,
            detail=(
                "Live Foundry mode is not configured on the server. Set "
                "AZURE_FOUNDRY_PROJECT_ENDPOINT (and sign in with Azure) to enable it."
            ),
        )


@router.get("/sequential", response_model=SequentialRunResult)
def get_sequential(
    facility: str = Query(..., examples=["NJ-01"], description="Facility code"),
    foundry: FoundryMode | None = Query(
        None, description="Foundry reasoning mode: 'mock' (offline) or 'live' (Azure)."
    ),
) -> SequentialRunResult:
    """Option A — deterministic single-facility replenishment review."""
    _check_live(foundry)
    try:
        return FoundryClient().run_sequential(facility, foundry)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/multiagent", response_model=MultiAgentRunResult)
def get_multiagent(
    facilities: list[str] = Query(..., examples=[["NJ-01", "CA-02"]]),
    foundry: FoundryMode | None = Query(
        None, description="Foundry reasoning mode: 'mock' (offline) or 'live' (Azure)."
    ),
) -> MultiAgentRunResult:
    """Option B — multi-agent cross-facility planning with a ranked plan."""
    _check_live(foundry)
    try:
        return FoundryClient().run_multiagent(facilities, foundry)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
