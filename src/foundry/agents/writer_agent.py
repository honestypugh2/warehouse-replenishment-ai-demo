"""D365 Writer agent — the ONLY agent allowed to mutate D365.

The writer runs strictly after an explicit human approval signal. Every write is
logged with an audit id. No other agent in either workflow touches D365 state.
"""

from __future__ import annotations

from app.models.schemas import ApprovalRequest, D365WriteResponse
from app.services.d365_client import D365Client


def write(req: ApprovalRequest) -> D365WriteResponse:
    if req.new_min < 0 or req.new_max <= req.new_min:
        raise ValueError("Invalid min/max range: max must be greater than min.")
    return D365Client().write_min_max(req)
