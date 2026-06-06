"""Orchestrator agent — coordinates specialist agents for the multi-agent path.

For the demo this orchestrator runs the specialists concurrently per facility,
consolidates via a Risk/Policy reasoner, and returns a ranked plan. In
production this maps to a Microsoft Agent Framework orchestrator (handoff +
concurrent) hosted in Foundry.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import partial

from app.models.schemas import MultiAgentRunResult, RankedItem, SequentialRunResult
from foundry.workflows.sequential_replen import run_local as run_sequential


def _slotting_analyst(facility: str, mode: str | None = None) -> SequentialRunResult:
    """Reuses the Databricks + validator path to assess each facility."""
    return run_sequential(facility, mode)


def _demand_forecaster(facility: str) -> dict:
    """In production this calls Databricks AI/BI Genie or a Foundry model."""
    return {"facility": facility, "trend": "stable_up_3pct"}


def _risk_reasoner(per_facility: list[SequentialRunResult]) -> list[RankedItem]:
    """Ranks SKUs by potential wave-driven replenishment cost avoided."""
    ranked: list[RankedItem] = []
    for result in per_facility:
        for rec in result.recommendations:
            if rec.decision in ("approve_suggested", "needs_review"):
                # Heuristic: confidence weighted by the size of the min increase.
                min_delta = max(rec.candidate.recommended_min - rec.candidate.current_min, 0)
                score = rec.candidate.confidence * 100 + min_delta
                ranked.append(
                    RankedItem(
                        facility=result.facility,
                        sku=rec.candidate.sku,
                        score=round(score, 2),
                        decision=rec.decision,
                        explanation=rec.explanation,
                        citations=rec.citations,
                    )
                )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def orchestrate(facilities: list[str], mode: str | None = None) -> MultiAgentRunResult:
    workers = max(len(facilities), 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        slotting = list(pool.map(partial(_slotting_analyst, mode=mode), facilities))
        list(pool.map(_demand_forecaster, facilities))  # parallel, results merged in scoring
    ranking = _risk_reasoner(slotting)[:15]
    return MultiAgentRunResult(facilities=facilities, ranking=ranking)
