"""D365 F&O client.

D365 F&O is the *system of record*. This client reads operational state (open
orders, active waves) for validation and writes approved min-max values.

The production write path uses an MCP server for D365 or the F&O Data Management
Framework (DMF) entity for stocking limits. Writes are *only* performed after an
explicit human approval and are always logged with an audit id.
"""

from __future__ import annotations

import uuid

from app.config import settings
from app.mocks import d365_mock
from app.models.schemas import ApprovalRequest, D365WriteResponse


class D365Client:
    def __init__(self) -> None:
        self.mock = settings.mock_mode

    def get_open_orders(self, sku: str) -> list[dict]:
        if self.mock:
            return d365_mock.open_orders(sku)
        # PRODUCTION: OData GET /SalesOrderLines?$filter=ItemNumber eq '{sku}' and ...
        raise NotImplementedError("Wire the D365 open-orders read here.")

    def get_active_waves(self, facility: str) -> list[dict]:
        if self.mock:
            return d365_mock.active_waves(facility)
        # PRODUCTION: OData GET /WaveHeaders?$filter=WarehouseId eq '{facility}' and ...
        raise NotImplementedError("Wire the D365 active-waves read here.")

    def write_min_max(self, req: ApprovalRequest) -> D365WriteResponse:
        if self.mock:
            return D365WriteResponse(
                sku=req.sku,
                facility=req.facility,
                success=True,
                audit_id=f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
                message="Mock write OK — min-max persisted to D365 (simulated).",
            )
        # PRODUCTION: POST to the MCP D365 tool OR a DMF entity update
        # (e.g. InventStockingLimits). Use a scoped managed identity token.
        raise NotImplementedError("Wire the D365 MCP / DMF write here.")
