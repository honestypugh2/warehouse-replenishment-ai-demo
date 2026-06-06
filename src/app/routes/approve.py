"""Approval / rejection endpoints — the human-in-the-loop gate.

Only an approval here results in a D365 write, performed by the Writer agent.
A rejection records a deferral with an audit id and never writes.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ApprovalRequest,
    D365WriteResponse,
    RejectionRequest,
    RejectionResponse,
)
from foundry.agents.writer_agent import write

router = APIRouter(prefix="/approve", tags=["approve"])


@router.post("", response_model=D365WriteResponse)
def approve(req: ApprovalRequest) -> D365WriteResponse:
    if req.new_min < 0 or req.new_max <= req.new_min:
        raise HTTPException(400, "Invalid min/max range: max must be greater than min.")
    try:
        return write(req)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/reject", response_model=RejectionResponse)
def reject(req: RejectionRequest) -> RejectionResponse:
    return RejectionResponse(
        sku=req.sku,
        facility=req.facility,
        deferred=True,
        audit_id=f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
        message=f"Recommendation deferred: {req.reason}",
    )
