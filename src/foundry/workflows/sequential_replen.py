"""Sequential orchestration (Architecture Option A).

Deterministic pipeline:
    Retriever -> Validator -> Reasoner -> (Approval gate) -> (Writer) -> Auditor

``run_local`` executes the same pipeline in-process for demo mode. In production
this maps to a Microsoft Agent Framework SequentialOrchestration hosted in
Foundry, where the Approval gate waits on a Copilot Studio approval card and the
Writer runs only after approval.
"""

from __future__ import annotations

from app.models.schemas import SequentialRunResult
from foundry.agents import recommender_agent, retriever_agent, validator_agent


def run_local(facility: str, mode: str | None = None) -> SequentialRunResult:
    candidates = retriever_agent.retrieve(facility)
    recommendations = [
        recommender_agent.reason(candidate, validator_agent.validate(candidate), mode)
        for candidate in candidates
    ]
    return SequentialRunResult(
        facility=facility,
        count=len(recommendations),
        recommendations=recommendations,
    )
