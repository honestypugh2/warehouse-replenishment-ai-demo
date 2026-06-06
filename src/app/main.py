"""FastAPI application entrypoint.

Wires the routes for the AI Warehouse Replenishment Orchestration Demo:
Copilot Studio (hub) -> Foundry (engine) -> Databricks (intelligence) -> D365
(system of record). Runs in MOCK_MODE by default.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import approve, d365, recommendations, validate
from foundry.observability import configure_observability

# Export GenAI / workflow traces to App Insights when configured (no-op offline).
configure_observability()

app = FastAPI(
    title="AI Warehouse Replenishment Orchestration Demo API",
    description=(
        "Governed, human-in-the-loop warehouse replenishment using "
        "Copilot Studio, Microsoft Foundry, Databricks, and D365."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommendations.router)
app.include_router(validate.router)
app.include_router(approve.router)
app.include_router(d365.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {
        "ok": True,
        # Data systems are always mocked in this demo.
        "mock_mode": settings.mock_mode,
        "databricks_mode": "mock",
        "d365_mode": "mock",
        # Foundry reasoning can be mock (offline) or live (real Azure model).
        "foundry_mode": settings.foundry_mode,
        "foundry_live_available": settings.foundry_live_available,
        # Persistent Foundry agents + portal tracing/monitoring.
        "foundry_use_agents": settings.foundry_use_agents,
        "tracing_enabled": settings.tracing_enabled,
    }
