"""Multi-agent orchestration (Architecture Option B).

Demo-mode local simulation. In production this maps to a Microsoft Agent
Framework orchestrator coordinating specialist agents (Slotting Analyst, Demand
Forecaster, Ops Validator, Risk/Policy Reasoner, D365 Writer) via handoff and
concurrent patterns hosted in Foundry.
"""

from __future__ import annotations

from app.models.schemas import MultiAgentRunResult
from foundry.agents.orchestrator_agent import orchestrate


def run_local(facilities: list[str], mode: str | None = None) -> MultiAgentRunResult:
    return orchestrate(facilities, mode)
