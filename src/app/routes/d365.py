"""D365 operational-state read endpoints (open orders, active waves).

These expose the same reads the Validator performs so the frontend / Copilot
Studio can show planners the live D365 context behind a recommendation.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.d365_client import D365Client

router = APIRouter(prefix="/d365", tags=["d365"])


@router.get("/orders")
def open_orders(sku: str = Query(..., examples=["CAB-750-12"])) -> list[dict]:
    return D365Client().get_open_orders(sku)


@router.get("/waves")
def active_waves(facility: str = Query(..., examples=["NJ-01"])) -> list[dict]:
    return D365Client().get_active_waves(facility)
