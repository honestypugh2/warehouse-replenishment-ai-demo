"""Foundry client.

Runs the replenishment orchestration. In this demo the data flow (Databricks
signals, D365 state) is always mocked and runs in-process; the only part that
can talk to a real Azure model is the *reasoning narration*, controlled by the
Foundry mode:

* ``mock`` — narration uses a deterministic local template (fully offline).
* ``live`` — narration uses a real Azure AI Foundry model deployment.

Decisions and guardrails are deterministic in both modes.
"""

from __future__ import annotations

from app.config import settings
from app.models.schemas import MultiAgentRunResult, SequentialRunResult


class FoundryClient:
    def run_sequential(
        self, facility: str, mode: str | None = None
    ) -> SequentialRunResult:
        # Prefers the Agent Framework workflow over the persistent Foundry agents
        # when FOUNDRY_USE_AGENTS=true; otherwise falls back to the in-process
        # pipeline. Either way the decisions and numbers are identical.
        from foundry.workflows.foundry_agent_workflow import run_sequential

        return run_sequential(facility, settings.resolve_foundry_mode(mode))

    def run_multiagent(
        self, facilities: list[str], mode: str | None = None
    ) -> MultiAgentRunResult:
        from foundry.workflows.multiagent_replen import run_local

        return run_local(facilities, settings.resolve_foundry_mode(mode))
